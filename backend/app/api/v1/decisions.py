from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_session
from app.models.decision import DecisionRun, WorkflowTask
from app.models.domain import TradeCase
from app.rules.workflow import ACTORS, DemoActor
from app.schemas.advisory import AdvisoryRequest
from app.schemas.decision import (
    AuditEntry,
    DecisionDetail,
    DecisionSummary,
    Event,
    Override,
    Reason,
    Resolution,
    StartDecision,
    Task,
    TaskDetail,
    Workflow,
)
from app.schemas.workflow import OverrideRequest, TaskActionRequest
from app.services.case_audit import case_audit
from app.services.decision_engine import (
    decision_is_current,
    generate_decision,
    get_decision,
    latest_source,
)
from app.services.decision_overrides import apply_override
from app.services.exception_advisor import draft_exception_advice
from app.services.fact_resolver import case_by_id
from app.services.governed_workflow import act_on_task, action_choices, unresolved_reason_ids
from app.services.workflow_controls import demo_actor, maker_actor_ids

router = APIRouter(prefix="/api/v1", tags=["Governed decisions and demo workflow"])
Database = Annotated[Session, Depends(get_session)]


def summary(session, run):
    return DecisionSummary.model_validate(run).model_copy(
        update={"case_id": session.get(TradeCase, run.case_pk).case_id}
    )


def detail(session, run, actor_id="maker.demo"):
    actor = demo_actor(actor_id)
    current = decision_is_current(session, get_settings(), run)
    return DecisionDetail(
        run=summary(session, run),
        input_snapshot=run.input_snapshot_json,
        reasons=[Reason.model_validate(r) for r in run.reasons],
        workflow=Workflow.model_validate(run.workflow) if run.workflow else None,
        tasks=[
            Task.model_validate(t).model_copy(
                update={"available_actions": action_choices(run, t, actor, current)}
            )
            for t in run.tasks
        ],
        events=[Event.model_validate(e) for e in run.events],
        overrides=[Override.model_validate(o) for o in run.overrides],
        resolutions=[Resolution.model_validate(r) for r in run.resolutions],
        inputs_current=current,
        effective_final_outcome=run.workflow.final_outcome if current and run.workflow else None,
        unresolved_reason_ids=sorted(unresolved_reason_ids(run)),
        maker_actor_ids=sorted(maker_actor_ids(run)),
        demo_actor=actor,
    )


@router.get("/demo-actors", response_model=list[DemoActor])
def actors():
    return list(ACTORS.values())


@router.post("/cases/{case_id}/decisions", response_model=DecisionDetail)
def start(case_id: str, session: Database, payload: StartDecision | None = None):
    payload = payload or StartDecision()
    return detail(
        session, generate_decision(session, get_settings(), case_id, str(payload.request_id))
    )


@router.get("/cases/{case_id}/decisions", response_model=list[DecisionSummary])
def history(case_id: str, session: Database):
    case = case_by_id(session, case_id)
    return [
        summary(session, r)
        for r in session.scalars(
            select(DecisionRun)
            .where(DecisionRun.case_pk == case.id)
            .order_by(DecisionRun.run_number.desc())
        )
    ]


@router.get("/cases/{case_id}/decisions/latest", response_model=DecisionDetail)
def latest(case_id: str, session: Database, actor_id: str = "maker.demo"):
    case = case_by_id(session, case_id)
    run = latest_source(session, DecisionRun, case.id)
    if run is None:
        raise HTTPException(404, "No decision exists for this case")
    return detail(session, get_decision(session, run.id), actor_id)


@router.get("/decisions/{id}", response_model=DecisionDetail)
def read(id: int, session: Database, actor_id: str = "maker.demo"):
    return detail(session, get_decision(session, id), actor_id)


@router.get("/decisions/{id}/reasons", response_model=list[Reason])
def reasons(id: int, session: Database):
    return [Reason.model_validate(r) for r in get_decision(session, id).reasons]


@router.get("/cases/{case_id}/tasks", response_model=list[Task])
def tasks(case_id: str, session: Database, actor_id: str = "maker.demo"):
    case = case_by_id(session, case_id)
    run = latest_source(session, DecisionRun, case.id)
    return detail(session, get_decision(session, run.id), actor_id).tasks if run else []


@router.get("/tasks/{id}", response_model=TaskDetail)
def task(id: int, session: Database, actor_id: str = "maker.demo"):
    item = session.get(WorkflowTask, id)
    if item is None:
        raise HTTPException(404, "Workflow task not found")
    data = detail(session, get_decision(session, item.decision_run_pk), actor_id)
    return TaskDetail(
        task=next(t for t in data.tasks if t.id == id),
        decision=data.run,
        workflow=data.workflow,
        inputs_current=data.inputs_current,
    )


@router.post("/tasks/{id}/actions", response_model=DecisionDetail)
def action(id: int, session: Database, payload: TaskActionRequest):
    return detail(session, act_on_task(session, get_settings(), id, payload), payload.actor_id)


@router.post("/decisions/{id}/override", response_model=DecisionDetail)
def override(id: int, session: Database, payload: OverrideRequest):
    return detail(session, apply_override(session, get_settings(), id, payload), payload.actor_id)


@router.post("/decisions/{id}/exception-summary")
def advisory(id: int, session: Database, payload: AdvisoryRequest):
    return draft_exception_advice(session, get_settings(), id, payload)


@router.get("/cases/{case_id}/audit", response_model=list[AuditEntry])
def audit(case_id: str, session: Database):
    return case_audit(session, case_id)


@router.get("/cases/{case_id}/workflow")
def workflow(case_id: str, session: Database, actor_id: str = "maker.demo"):
    case = case_by_id(session, case_id)
    run = latest_source(session, DecisionRun, case.id)
    if run is None:
        return {
            "case_id": case_id,
            "state": "READY_FOR_DECISION",
            "final_outcome": None,
            "effective_final_outcome": None,
            "decision_id": None,
            "demo_only": True,
        }
    data = detail(session, get_decision(session, run.id), actor_id)
    return {
        "case_id": case_id,
        "decision_id": run.id,
        "workflow": data.workflow,
        "inputs_current": data.inputs_current,
        "effective_final_outcome": data.effective_final_outcome,
        "demo_only": True,
    }
