from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_session
from app.models.domain import TradeCase
from app.schemas.risk import Check, Finding, RiskDetail, RiskExecution, RiskSummary, StartRiskRun
from app.services.duplicate_trade import (
    duplicate_candidates,
    invoice_profiles,
    load_current_corpora,
)
from app.services.fact_resolver import case_by_id
from app.services.risk_orchestration import (
    get_risk_run,
    risk_history,
    risk_inputs_current,
    run_risk_checks,
)

router = APIRouter(prefix="/api/v1", tags=["Risk and compliance"])
Database = Annotated[Session, Depends(get_session)]


def summary(session, run):
    case = session.get(TradeCase, run.case_pk)
    return RiskSummary.model_validate(run).model_copy(update={"case_id": case.case_id})


def detail(session, run):
    return RiskDetail(
        run=summary(session, run),
        checks=[Check.model_validate(c) for c in run.checks],
        executions=[RiskExecution.model_validate(e) for e in run.executions],
        findings=[Finding.model_validate(f) for f in run.findings],
        inputs_current=risk_inputs_current(session, get_settings(), run),
    )


@router.post("/cases/{case_id}/risk-runs", response_model=RiskDetail)
def start(case_id: str, session: Database, payload: StartRiskRun | None = None):
    payload = payload or StartRiskRun()
    return detail(
        session, run_risk_checks(session, get_settings(), case_id, str(payload.request_id))
    )


@router.get("/cases/{case_id}/risk-runs", response_model=list[RiskSummary])
def history(case_id: str, session: Database):
    return [summary(session, r) for r in risk_history(session, case_id)]


@router.get("/cases/{case_id}/risk-runs/latest", response_model=RiskDetail)
def latest(case_id: str, session: Database):
    runs = risk_history(session, case_id)
    if not runs:
        raise HTTPException(404, "No risk run exists for this case")
    return detail(session, get_risk_run(session, runs[0].id))


@router.get("/risk-runs/{run_id}", response_model=RiskDetail)
def read(run_id: int, session: Database):
    return detail(session, get_risk_run(session, run_id))


@router.get("/risk-runs/{run_id}/provider-checks", response_model=list[Check])
def checks(run_id: int, session: Database):
    return [Check.model_validate(c) for c in get_risk_run(session, run_id).checks]


@router.get("/risk-runs/{run_id}/rule-executions", response_model=list[RiskExecution])
def executions(run_id: int, session: Database):
    return [RiskExecution.model_validate(e) for e in get_risk_run(session, run_id).executions]


@router.get("/risk-runs/{run_id}/findings", response_model=list[Finding])
def findings(run_id: int, session: Database):
    return [Finding.model_validate(f) for f in get_risk_run(session, run_id).findings]


@router.get("/cases/{case_id}/duplicate-candidates")
def duplicates(case_id: str, session: Database):
    case_by_id(session, case_id)
    profiles = invoice_profiles(
        load_current_corpora(session), get_settings().examination_min_confidence
    )
    return {
        "case_id": case_id,
        "candidates": [
            {"current_invoice": p, "candidates": duplicate_candidates(p, profiles)}
            for p in profiles
            if p["case_id"] == case_id
        ],
        "financing_status": "NOT_CHECKED",
        "synthetic": True,
    }
