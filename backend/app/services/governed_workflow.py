"""Atomic human actions over immutable recommendations and appended audit evidence."""

from sqlalchemy import select

from app.models.decision import DecisionRun, FindingResolution, WorkflowTask
from app.models.domain import TradeCase, now
from app.rules.decision import POLICY
from app.rules.workflow import SPECIALIST_TASKS, Action, EventType, TaskType, WorkflowState
from app.services.decision_engine import decision_is_current, get_decision
from app.services.examination_engine import fingerprint
from app.services.workflow_audit import create_task, record_event
from app.services.workflow_controls import (
    WorkflowConflict,
    WorkflowForbidden,
    authorize,
    demo_actor,
    enforce_sod,
)


def unresolved_reason_ids(run):
    resolved = set()
    latest = {r.decision_reason_pk: r.resolution for r in run.resolutions}
    for id, result in latest.items():
        if result == Action.CLEAR:
            resolved.add(id)
    for override in run.overrides:
        resolved.update(override.reason_ids_json)
    return {r.id for r in run.reasons if r.impact != "INFO"} - resolved


def reason_clearable(reason):
    # Review-level risk identity/policy uncertainty can be cleared by its specialist.
    # A real documentary mismatch or missing evidence cannot be erased by a comment.
    return reason.reason_code == "RISK_REVIEW"


def open_tasks(run, kinds=None):
    return [
        t
        for t in run.tasks
        if t.status in {"OPEN", "IN_PROGRESS"} and (kinds is None or t.task_type in kinds)
    ]


def action_choices(run, task, actor, current):
    if not current or not run.workflow or run.workflow.final_outcome:
        return []
    try:
        authorize(actor, task.assigned_role)
        if task.task_type == TaskType.CHECKER:
            enforce_sod(run, actor)
    except WorkflowForbidden:
        return []
    if task.status not in {"OPEN", "IN_PROGRESS"}:
        return []
    if task.status == "IN_PROGRESS" and task.assigned_actor_id != actor.actor_id:
        return []
    if run.recommended_decision == "BLOCK":
        choices = [Action.ACKNOWLEDGE_BLOCK] if task.task_type == TaskType.ESCALATION else []
    elif task.task_type == TaskType.MAKER:
        choices = [Action.SUBMIT, Action.INFORMATION, Action.REFER, Action.REJECT]
        if run.workflow.state != WorkflowState.MAKER or unresolved_reason_ids(run):
            choices.remove(Action.SUBMIT)
    elif task.task_type == TaskType.CHECKER:
        choices = [Action.APPROVE, Action.RETURN, Action.REFER, Action.REJECT]
        if run.workflow.state != WorkflowState.CHECKER or unresolved_reason_ids(run):
            choices.remove(Action.APPROVE)
    elif task.task_type == TaskType.INFORMATION:
        choices = [Action.PROVIDED]
    else:
        choices = [Action.ISSUE, Action.INFORMATION, Action.ESCALATE]
        reasons = [r for r in run.reasons if r.id in task.reason_ids_json]
        if all(reason_clearable(r) for r in reasons):
            choices.insert(0, Action.CLEAR)
    if choices and task.status == "OPEN":
        choices.insert(0, Action.START)
    return choices


def lock_run(session, id):
    run = session.get(DecisionRun, id)
    if run is None:
        return get_decision(session, id)
    session.scalar(select(TradeCase).where(TradeCase.id == run.case_pk).with_for_update())
    return get_decision(session, id)


def command_repeated(run, payload, command):
    digest = fingerprint({"command": command, "payload": payload.model_dump(mode="json")})
    for event in run.events:
        if event.request_id == str(payload.request_id):
            if (
                event.actor_id != payload.actor_id
                or event.metadata_json.get("command_fingerprint") != digest
            ):
                raise WorkflowConflict("Request identity already belongs to a different action")
            return True, digest
    return False, digest


def assert_action_current(session, settings, run, revision):
    if not decision_is_current(session, settings, run):
        raise WorkflowConflict(
            "Decision is stale; regenerate from the latest examination and risk runs"
        )
    if not run.workflow or run.workflow.revision != revision:
        raise WorkflowConflict("Workflow changed; refresh before acting")
    if run.workflow.final_outcome:
        raise WorkflowConflict("Governed outcome is already finalized")


def refresh_run(session, run):
    session.flush()
    return get_decision(session, run.id)


def advance(session, run):
    run = refresh_run(session, run)
    workflow = run.workflow
    if open_tasks(run, {TaskType.INFORMATION}):
        workflow.state = WorkflowState.INFORMATION
        return
    if open_tasks(run, SPECIALIST_TASKS):
        workflow.state = WorkflowState.SPECIALIST
        return
    remaining = unresolved_reason_ids(run)
    if remaining:
        nonwaivable = [
            r.id
            for r in run.reasons
            if r.id in remaining and r.reason_code not in POLICY.overrideable_codes
        ]
        if nonwaivable:
            workflow.state = WorkflowState.INFORMATION
            create_task(session, run, TaskType.INFORMATION, nonwaivable)
        else:
            workflow.state = WorkflowState.REFERRED
            if not open_tasks(run, {TaskType.ESCALATION}):
                create_task(session, run, TaskType.ESCALATION, sorted(remaining), priority="HIGH")
        return
    if open_tasks(run, {TaskType.ESCALATION}):
        workflow.state = WorkflowState.REFERRED
        return
    workflow.state = WorkflowState.MAKER
    if not open_tasks(run, {TaskType.MAKER}):
        create_task(session, run, TaskType.MAKER)


def cancel_remaining(session, run, keep=None):
    for other in open_tasks(refresh_run(session, run)):
        if not keep or other.id != keep.id:
            other.status, other.completed_at = "CANCELLED", now()
            record_event(session, run, EventType.CANCEL, task=other)


def act_on_task(session, settings, task_id, payload):
    try:
        return _act_on_task(session, settings, task_id, payload)
    except Exception:
        session.rollback()
        raise


def _act_on_task(session, settings, task_id, payload):
    task = session.get(WorkflowTask, task_id)
    if task is None:
        from app.services.decision_engine import DecisionNotFound

        raise DecisionNotFound
    run = lock_run(session, task.decision_run_pk)
    task = next(t for t in run.tasks if t.id == task_id)
    actor = demo_actor(payload.actor_id)
    authorize(actor, task.assigned_role)
    if task.task_type == TaskType.CHECKER:
        enforce_sod(run, actor)
    repeated, digest = command_repeated(run, payload, f"task:{task.id}")
    if repeated:
        return run
    assert_action_current(session, settings, run, payload.expected_revision)
    if payload.action not in action_choices(run, task, actor, True):
        raise WorkflowConflict("Action is not allowed for this task and workflow state")
    action = payload.action
    if task.status == "OPEN":
        task.assigned_actor_id, task.assigned_at = actor.actor_id, now()
    workflow = run.workflow
    event_type = EventType.START
    metadata = {"action": action, "command_fingerprint": digest}
    if action == Action.START:
        task.status = "IN_PROGRESS"
    elif action == Action.INFORMATION:
        task.status = "IN_PROGRESS"
        information = create_task(session, run, TaskType.INFORMATION, task.reason_ids_json)
        metadata.update(information_task_id=information.id, parent_task_id=task.id)
        workflow.state, event_type = WorkflowState.INFORMATION, EventType.INFORMATION
    else:
        task.status, task.completed_at, task.resolution = "COMPLETED", now(), action
        if action == Action.SUBMIT:
            if open_tasks(run, SPECIALIST_TASKS | {TaskType.INFORMATION, TaskType.ESCALATION}):
                raise WorkflowConflict("Open specialist/information tasks prevent maker submission")
            workflow.maker_actor_id = actor.actor_id
            workflow.state, event_type = WorkflowState.CHECKER, EventType.MAKER
            create_task(session, run, TaskType.CHECKER)
        elif action == Action.APPROVE:
            if not workflow.maker_actor_id or open_tasks(
                run, SPECIALIST_TASKS | {TaskType.INFORMATION, TaskType.ESCALATION}
            ):
                raise WorkflowConflict("Maker and all specialist controls must be complete")
            workflow.state, workflow.final_outcome = WorkflowState.APPROVED, "PASS"
            workflow.checker_actor_id, workflow.finalized_at = actor.actor_id, now()
            event_type = EventType.APPROVE
        elif action == Action.RETURN:
            workflow.state, workflow.maker_actor_id = WorkflowState.MAKER, None
            event_type = EventType.RETURN
            create_task(session, run, TaskType.MAKER)
        elif action == Action.REFER:
            workflow.state, workflow.maker_actor_id = WorkflowState.SPECIALIST, None
            event_type = EventType.REFER
            create_task(session, run, TaskType.TRADE)
        elif action == Action.REJECT:
            workflow.state, workflow.final_outcome = WorkflowState.REJECTED, "REJECT"
            workflow.finalized_at, event_type = now(), EventType.REJECT
            cancel_remaining(session, run, task)
        elif action == Action.ACKNOWLEDGE_BLOCK:
            workflow.state, workflow.final_outcome = WorkflowState.BLOCKED, "BLOCK"
            workflow.finalized_at, event_type = now(), EventType.BLOCK
            cancel_remaining(session, run, task)
        elif action in {Action.CLEAR, Action.ISSUE, Action.ESCALATE}:
            event_type = {
                Action.CLEAR: EventType.CLEAR,
                Action.ISSUE: EventType.ISSUE,
                Action.ESCALATE: EventType.ESCALATE,
            }[action]
            if action == Action.ESCALATE:
                queue = payload.target_queue or TaskType.ESCALATION
                metadata["target_queue"] = queue
                create_task(session, run, queue, task.reason_ids_json)
        elif action == Action.PROVIDED:
            event_type = EventType.PROVIDED
            request = next(
                (
                    e
                    for e in reversed(run.events)
                    if e.event_type == EventType.INFORMATION
                    and e.metadata_json.get("information_task_id") == task.id
                ),
                None,
            )
            if request:
                parent = next(
                    t for t in run.tasks if t.id == request.metadata_json["parent_task_id"]
                )
                if parent.status == "IN_PROGRESS":
                    parent.status, parent.assigned_actor_id = "OPEN", None
                    metadata["reopened_task_id"] = parent.id
    event = record_event(
        session,
        run,
        event_type,
        actor_id=actor.actor_id,
        actor_role=task.assigned_role,
        comment=payload.comment,
        task=task,
        metadata=metadata,
        request_id=str(payload.request_id),
    )
    if action in {Action.CLEAR, Action.ISSUE, Action.ESCALATE}:
        for id in task.reason_ids_json:
            session.add(
                FindingResolution(
                    decision_run_pk=run.id,
                    decision_reason_pk=id,
                    task_pk=task.id,
                    workflow_event_pk=event.id,
                    actor_id=actor.actor_id,
                    actor_role=task.assigned_role,
                    resolution=action,
                    rationale=payload.comment,
                )
            )
        advance(session, run)
    elif action == Action.PROVIDED:
        advance(session, run)
    if action == Action.APPROVE:
        record_event(
            session,
            run,
            EventType.PASS,
            actor_id=actor.actor_id,
            actor_role=task.assigned_role,
            comment=payload.comment,
        )
    workflow.revision += 1
    session.commit()
    return get_decision(session, run.id)
