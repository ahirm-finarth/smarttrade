from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.repositories.cases import CaseRepository
from app.schemas.cases import (
    Approval,
    CaseDetail,
    CaseList,
    DashboardSummary,
    Document,
    Finding,
    Line,
    Party,
    Risk,
)
from app.services.cases import CaseService

router = APIRouter(prefix="/api/v1")


def get_service(session: Annotated[Session, Depends(get_session)]):
    return CaseService(CaseRepository(session))


Service = Annotated[CaseService, Depends(get_service)]


@router.get("/cases", response_model=CaseList)
def list_cases(
    service: Service,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None, max_length=200),
    product: str | None = Query(None, max_length=100),
    outcome: str | None = Query(None, max_length=16),
):
    return service.list(limit, offset, q, product, outcome)


@router.get("/cases/{case_id}", response_model=CaseDetail)
def get_case(case_id: str, service: Service):
    return service.detail(case_id)


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(service: Service):
    return service.summary()


@router.get("/cases/{case_id}/parties", response_model=list[Party])
def parties(case_id: str, service: Service):
    return service.detail(case_id).parties


@router.get("/cases/{case_id}/documents", response_model=list[Document])
def documents(case_id: str, service: Service):
    return service.detail(case_id).documents


@router.get("/cases/{case_id}/trade-lines", response_model=list[Line])
def trade_lines(case_id: str, service: Service):
    return service.detail(case_id).trade_lines


@router.get("/cases/{case_id}/discrepancies", response_model=list[Finding])
def discrepancies(case_id: str, service: Service):
    return service.detail(case_id).discrepancies


@router.get("/cases/{case_id}/risk-events", response_model=list[Risk])
def risks(case_id: str, service: Service):
    return service.detail(case_id).risk_events


@router.get("/cases/{case_id}/approvals", response_model=list[Approval])
def approvals(case_id: str, service: Service):
    return service.detail(case_id).approvals
