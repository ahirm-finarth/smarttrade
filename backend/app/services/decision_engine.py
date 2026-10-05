"""Versioned immutable recommendations from exact current source runs."""

from collections import Counter, defaultdict
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import Settings
from app.models.decision import DecisionReason, DecisionRun, GovernedWorkflow, WorkflowTask
from app.models.domain import TradeCase, now
from app.models.examination import ExaminationRun
from app.models.risk import RiskRun
from app.rules.decision import POLICY, DecisionCase, DecisionInput, evaluate
from app.rules.workflow import ROUTING, EventType, TaskType, WorkflowState, route_reason
from app.schemas.examination import Execution, Finding
from app.schemas.risk import Check, RiskExecution
from app.schemas.risk import Finding as RiskFinding
from app.services.documents import DocumentConflict
from app.services.examination_engine import examination_is_current, fingerprint, get_examination
from app.services.fact_resolver import case_by_id
from app.services.risk_orchestration import get_risk_run, risk_inputs_current
from app.services.workflow_audit import create_task, record_event


class DecisionNotFound(Exception):
    pass


def latest_source(session, model, case_pk):
    return session.scalar(
        select(model).where(model.case_pk == case_pk).order_by(model.run_number.desc()).limit(1)
    )


def decision_context(session, settings, case_id):
    case = case_by_id(session, case_id)
    documentary = latest_source(session, ExaminationRun, case.id)
    risk = latest_source(session, RiskRun, case.id)
    doc_data, risk_data = None, None
    if documentary:
        documentary = get_examination(session, documentary.id)
        doc_data = {
            "id": documentary.id,
            "run_number": documentary.run_number,
            "status": documentary.status,
            "input_fingerprint": documentary.input_fingerprint,
            "summary": documentary.summary_json,
            "findings": [
                Finding.model_validate(f).model_dump(mode="json") for f in documentary.findings
            ],
            "executions": [
                Execution.model_validate(e).model_dump(mode="json") for e in documentary.executions
            ],
        }
    if risk:
        risk = get_risk_run(session, risk.id)
        risk_data = {
            "id": risk.id,
            "run_number": risk.run_number,
            "status": risk.status,
            "input_fingerprint": risk.input_fingerprint,
            "summary": risk.summary_json,
            "findings": [
                RiskFinding.model_validate(f).model_dump(mode="json") for f in risk.findings
            ],
            "checks": [Check.model_validate(c).model_dump(mode="json") for c in risk.checks],
            "executions": [
                RiskExecution.model_validate(e).model_dump(mode="json") for e in risk.executions
            ],
        }
    inputs = DecisionInput(
        case=DecisionCase(
            case_id=case.case_id,
            product_playbook=case.product_playbook,
            currency=case.currency,
            amount=str(case.amount) if case.amount is not None else None,
        ),
        documentary=doc_data,
        risk=risk_data,
        documentary_current=bool(
            documentary and examination_is_current(session, documentary, settings)
        ),
        risk_current=bool(risk and risk_inputs_current(session, settings, risk)),
    )
    snapshot = {**inputs.model_dump(mode="json"), "routing_policy": ROUTING.model_dump(mode="json")}
    return case, inputs, snapshot


def get_decision(session, id):
    run = session.scalar(
        select(DecisionRun)
        .where(DecisionRun.id == id)
        .options(
            selectinload(DecisionRun.reasons),
            selectinload(DecisionRun.workflow),
            selectinload(DecisionRun.tasks),
            selectinload(DecisionRun.events),
            selectinload(DecisionRun.overrides),
            selectinload(DecisionRun.resolutions),
        )
        .execution_options(populate_existing=True)
    )
    if run is None:
        raise DecisionNotFound
    return run


def decision_is_current(session, settings, run):
    latest = latest_source(session, DecisionRun, run.case_pk)
    if not latest or latest.id != run.id or run.status != "COMPLETED":
        return False
    case = session.get(TradeCase, run.case_pk)
    _, inputs, snapshot = decision_context(session, settings, case.case_id)
    return (
        inputs.documentary_current
        and inputs.risk_current
        and fingerprint(snapshot) == run.input_fingerprint
    )


def generate_decision(session, settings: Settings, case_id, request_id=None):
    case = session.scalar(select(TradeCase).where(TradeCase.case_id == case_id).with_for_update())
    if case is None:
        case_by_id(session, case_id)
    key = str(request_id or uuid4())
    repeated = session.scalar(
        select(DecisionRun).where(DecisionRun.case_pk == case.id, DecisionRun.request_id == key)
    )
    if repeated:
        return get_decision(session, repeated.id)
    latest = latest_source(session, DecisionRun, case.id)
    if latest and latest.status == "RUNNING":
        if latest.started_at > now() - timedelta(minutes=5):
            session.rollback()
            raise DocumentConflict("Decision generation is already running")
        latest.status, latest.completed_at = "FAILED", now()
        latest.error_message = "Previous decision worker expired"
    _, inputs, snapshot = decision_context(session, settings, case_id)
    run = DecisionRun(
        case_pk=case.id,
        run_number=latest.run_number + 1 if latest else 1,
        request_id=key,
        examination_run_pk=inputs.documentary["id"] if inputs.documentary else None,
        risk_run_pk=inputs.risk["id"] if inputs.risk else None,
        ruleset_version=POLICY.version,
        status="RUNNING",
        input_snapshot_json=snapshot,
        input_fingerprint=fingerprint(snapshot),
    )
    session.add(run)
    session.commit()
    id = run.id
    try:
        result = evaluate(inputs)
        queues = defaultdict(list)
        for data in result["reasons"]:
            queue = route_reason(data, case.product_playbook)
            reason = DecisionReason(decision_run_pk=run.id, **data, route_to=queue)
            session.add(reason)
            session.flush()
            if queue:
                queues[queue].append(reason.id)
        run.recommended_decision = result["recommended_decision"]
        state = (
            WorkflowState.BLOCKED
            if run.recommended_decision == "BLOCK"
            else WorkflowState.SPECIALIST
            if queues
            else WorkflowState.MAKER
        )
        session.add(GovernedWorkflow(case_pk=case.id, decision_run_pk=run.id, state=state))
        record_event(
            session,
            run,
            EventType.DECISION,
            metadata={
                "recommended_decision": run.recommended_decision,
                "examination_run_id": run.examination_run_pk,
                "risk_run_id": run.risk_run_pk,
                "ruleset_version": run.ruleset_version,
            },
        )
        if queues:
            for queue, ids in sorted(queues.items()):
                create_task(
                    session,
                    run,
                    queue,
                    ids,
                    priority="CRITICAL" if run.recommended_decision == "BLOCK" else "HIGH",
                )
        else:
            create_task(session, run, TaskType.MAKER)
        if run.recommended_decision == "BLOCK":
            record_event(session, run, EventType.BLOCK)
        if latest and latest.status == "COMPLETED":
            record_event(
                session, latest, EventType.SUPERSEDED, metadata={"new_decision_id": run.id}
            )
            for task in session.scalars(
                select(WorkflowTask).where(
                    WorkflowTask.decision_run_pk == latest.id,
                    WorkflowTask.status.in_(["OPEN", "IN_PROGRESS"]),
                )
            ):
                task.status, task.completed_at = "CANCELLED", now()
                record_event(
                    session,
                    latest,
                    EventType.CANCEL,
                    task=task,
                    metadata={"new_decision_id": run.id},
                )
        impacts = Counter(r["impact"] for r in result["reasons"])
        run.summary_json = {
            "reasons": len(result["reasons"]),
            "blocking_reasons": impacts["REFER"] + impacts["BLOCK"],
            "optional_unchecked": sum(
                r["reason_code"] == "OPTIONAL_CONTROL_UNCHECKED" for r in result["reasons"]
            ),
            "documentary_findings": len(inputs.documentary["findings"])
            if inputs.documentary
            else 0,
            "risk_findings": len(inputs.risk["findings"]) if inputs.risk else 0,
            "by_impact": dict(impacts),
            "required_approvals": list(POLICY.required_approvals),
        }
        run.status, run.completed_at = "COMPLETED", now()
        session.commit()
    except Exception:
        session.rollback()
        run = session.get(DecisionRun, id)
        run.status, run.completed_at = "FAILED", now()
        run.error_message = (
            "Decision generation failed; partial outputs rolled back. Retry explicitly."
        )
        session.commit()
    return get_decision(session, id)
