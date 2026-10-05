"""Supervisor acceptance of reviewed REFER exceptions; never a final approval."""

from app.models.decision import DecisionOverride
from app.models.domain import now
from app.rules.decision import POLICY
from app.rules.workflow import Action, EventType, Role, TaskType
from app.services.decision_engine import get_decision
from app.services.governed_workflow import (
    advance,
    assert_action_current,
    command_repeated,
    lock_run,
    open_tasks,
    refresh_run,
    unresolved_reason_ids,
)
from app.services.workflow_audit import record_event
from app.services.workflow_controls import WorkflowConflict, authorize, demo_actor


def apply_override(session, settings, id, payload):
    try:
        return _apply_override(session, settings, id, payload)
    except Exception:
        session.rollback()
        raise


def _apply_override(session, settings, id, payload):
    run = lock_run(session, id)
    actor = demo_actor(payload.actor_id)
    authorize(actor, Role.SUPERVISOR)
    repeated, digest = command_repeated(run, payload, "refer-override")
    if repeated:
        return run
    assert_action_current(session, settings, run, payload.expected_revision)
    if run.recommended_decision != "REFER":
        raise WorkflowConflict(
            "Only REFER exceptions may be accepted; hard BLOCK is non-overridable"
        )
    selected = set(payload.reason_ids)
    remaining = unresolved_reason_ids(run)
    if not selected.issubset(remaining):
        raise WorkflowConflict("Override must reference unresolved reasons from this decision")
    reasons = [r for r in run.reasons if r.id in selected]
    if any(r.reason_code not in POLICY.overrideable_codes for r in reasons):
        raise WorkflowConflict("Missing, incomplete or stale evidence cannot be waived")
    latest = {r.decision_reason_pk: r.resolution for r in run.resolutions}
    if any(latest.get(id) != Action.ISSUE for id in selected):
        raise WorkflowConflict("A specialist must confirm each issue before supervisory acceptance")
    event = record_event(
        session,
        run,
        EventType.OVERRIDE,
        actor_id=actor.actor_id,
        actor_role=Role.SUPERVISOR,
        comment=payload.rationale,
        metadata={
            "reason_ids": sorted(selected),
            "from_decision": "REFER",
            "to_decision": "PASS",
            "final_approval": False,
            "command_fingerprint": digest,
        },
        request_id=str(payload.request_id),
    )
    session.add(
        DecisionOverride(
            case_pk=run.case_pk,
            decision_run_pk=run.id,
            workflow_event_pk=event.id,
            actor_id=actor.actor_id,
            actor_role=Role.SUPERVISOR,
            from_decision="REFER",
            to_decision="PASS",
            reason_code=payload.reason_code,
            rationale=payload.rationale,
            reason_ids_json=sorted(selected),
            evidence_reference=payload.evidence_reference,
            previous_outcome=run.workflow.final_outcome,
        )
    )
    run = refresh_run(session, run)
    if not unresolved_reason_ids(run):
        for task in open_tasks(run, {TaskType.ESCALATION}):
            task.status, task.completed_at, task.resolution = "COMPLETED", now(), EventType.OVERRIDE
            task.assigned_actor_id, task.assigned_at = actor.actor_id, now()
            record_event(
                session,
                run,
                EventType.OVERRIDE,
                actor_id=actor.actor_id,
                actor_role=Role.SUPERVISOR,
                task=task,
                comment=payload.rationale,
                metadata={"override_event_id": event.id},
            )
    advance(session, run)
    run.workflow.revision += 1
    session.commit()
    return get_decision(session, run.id)
