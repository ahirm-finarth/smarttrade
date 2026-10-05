"""Controlled append-only events and auditable task creation."""

from sqlalchemy import func, select

from app.integrations.risk.contracts import assert_safe
from app.models.decision import WorkflowEvent, WorkflowTask
from app.rules.workflow import TASK_ROLES, EventType, TaskType


def record_event(
    session,
    run,
    event_type: EventType,
    *,
    actor_id="system",
    actor_role="SYSTEM",
    comment="",
    task=None,
    metadata=None,
    request_id=None,
):
    assert_safe({"comment": comment, "metadata": metadata or {}})
    event = WorkflowEvent(
        case_pk=run.case_pk,
        decision_run_pk=run.id,
        task_pk=task.id if task else None,
        event_type=EventType(event_type),
        actor_id=actor_id,
        actor_role=actor_role,
        comment=comment,
        metadata_json=metadata or {},
        request_id=request_id,
    )
    session.add(event)
    session.flush()
    return event


def create_task(session, run, kind: TaskType, reasons=(), *, priority="MEDIUM"):
    number = (
        session.scalar(
            select(func.count())
            .select_from(WorkflowTask)
            .where(WorkflowTask.decision_run_pk == run.id)
        )
        + 1
    )
    task = WorkflowTask(
        case_pk=run.case_pk,
        decision_run_pk=run.id,
        task_key=f"{kind}-{number}",
        task_type=kind,
        assigned_role=TASK_ROLES[kind],
        status="OPEN",
        priority=priority,
        title=kind.replace("_", " ").capitalize(),
        description=(
            "Review linked decision reasons and record rationale; "
            "original evidence remains unchanged."
        ),
        reason_ids_json=list(reasons),
    )
    session.add(task)
    session.flush()
    record_event(
        session,
        run,
        EventType.TASK,
        task=task,
        metadata={"assigned_role": task.assigned_role, "reason_ids": list(reasons)},
    )
    return task
