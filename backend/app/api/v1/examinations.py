from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_session
from app.models.domain import TradeCase
from app.schemas.examination import (
    CurrentCaseEvidence,
    ExaminationDetail,
    ExaminationSummary,
    Execution,
    Finding,
    Relation,
    StartExamination,
)
from app.services.examination_engine import (
    examination_history,
    examination_is_current,
    get_examination,
    run_examination,
)
from app.services.fact_resolver import case_by_id, load_case_evidence

router = APIRouter(prefix="/api/v1", tags=["Documentary examination"])
Database = Annotated[Session, Depends(get_session)]


def detail(session: Session, run) -> ExaminationDetail:
    case = session.get(TradeCase, run.case_pk)
    executions = [Execution.model_validate(e) for e in run.executions]
    by_id = {e.id: e for e in executions}
    relations = []
    for relation in run.relations:
        inputs = by_id[relation.rule_execution_pk].input_json
        relations.append(
            Relation.model_validate(relation).model_copy(
                update={"expected": inputs.expected.evidence, "observed": inputs.observed.evidence}
            )
        )
    return ExaminationDetail(
        run=ExaminationSummary.model_validate(run).model_copy(update={"case_id": case.case_id}),
        executions=executions,
        findings=[Finding.model_validate(f) for f in run.findings],
        relations=relations,
        inputs_current=examination_is_current(session, run),
    )


@router.post("/cases/{case_id}/examinations", response_model=ExaminationDetail)
def start(case_id: str, session: Database, payload: StartExamination | None = None):
    payload = payload or StartExamination()
    return detail(
        session, run_examination(session, get_settings(), case_id, str(payload.request_id))
    )


@router.get("/cases/{case_id}/examinations", response_model=list[ExaminationSummary])
def history(case_id: str, session: Database):
    return [
        ExaminationSummary.model_validate(r).model_copy(update={"case_id": case_id})
        for r in examination_history(session, case_id)
    ]


@router.get("/cases/{case_id}/examinations/latest", response_model=ExaminationDetail)
def latest(case_id: str, session: Database):
    runs = examination_history(session, case_id)
    if not runs:
        raise HTTPException(404, "No examination exists for this case")
    return detail(session, get_examination(session, runs[0].id))


@router.get("/examinations/{run_id}", response_model=ExaminationDetail)
def read(run_id: int, session: Database):
    return detail(session, get_examination(session, run_id))


@router.get("/examinations/{run_id}/rule-executions", response_model=list[Execution])
def executions(run_id: int, session: Database):
    return [Execution.model_validate(e) for e in get_examination(session, run_id).executions]


@router.get("/examinations/{run_id}/findings", response_model=list[Finding])
def findings(run_id: int, session: Database):
    return [Finding.model_validate(f) for f in get_examination(session, run_id).findings]


@router.get("/cases/{case_id}/evidence-relations", response_model=list[Relation])
def relations(case_id: str, session: Database, run_id: int | None = None):
    case = case_by_id(session, case_id)
    if run_id is None:
        runs = examination_history(session, case_id)
        if not runs:
            return []
        run_id = runs[0].id
    run = get_examination(session, run_id)
    if run.case_pk != case.id:
        raise HTTPException(404, "Examination does not belong to this case")
    return detail(session, run).relations


@router.get("/cases/{case_id}/extracted-facts", response_model=CurrentCaseEvidence)
def facts(case_id: str, session: Database):
    corpus = load_case_evidence(session, case_by_id(session, case_id))
    return {
        "case_id": case_id,
        "documents": [
            {k: v for k, v in d.items() if k not in {"facts", "pages"}} for d in corpus["documents"]
        ],
        "facts": [f for d in corpus["documents"] for f in d["facts"]],
        "confidence_threshold": get_settings().examination_min_confidence,
    }
