from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CaseSummary(ReadModel):
    case_id: str
    scenario: str | None
    product_playbook: str | None
    direction: str | None
    applicant: str | None
    beneficiary: str | None
    customer_id: str | None
    facility_id: str | None
    currency: str | None
    amount: Decimal | None
    priority: str | None
    status: str | None
    expected_decision: str | None
    demo_narrative: str | None
    created_at: datetime
    updated_at: datetime
    is_synthetic: bool = False


class Party(ReadModel):
    id: int
    party_role: str | None
    party_name: str | None
    country: str | None
    screening_status: str | None


class Document(ReadModel):
    id: int
    document_id: str | None
    document_type: str | None
    reference: str | None
    expected: bool | None
    received: bool | None
    file_name: str | None
    extraction_confidence: Decimal | None
    version_number: int | None = None
    page_count: int | None = None
    processing_status: str = "NOT_REGISTERED"
    detected_type: str | None = None
    extraction_status: str = "NOT_STARTED"
    source_updated_at: datetime | None = None


class Line(ReadModel):
    id: int
    source: str | None
    item_no: int | None
    goods_description: str | None
    quantity: Decimal | None
    uom: str | None
    unit_price: Decimal | None
    currency: str | None
    line_amount: Decimal | None


class Finding(ReadModel):
    id: int
    finding_id: str | None
    severity: str | None
    rule_id: str | None
    category: str | None
    field: str | None
    expected_value: str | None
    observed_value: str | None
    evidence: str | None
    route_to: str | None
    status: str | None


class Risk(ReadModel):
    id: int
    risk_id: str | None
    risk_type: str | None
    subject: str | None
    provider: str | None
    result: str | None
    severity: str | None
    reason: str | None


class Approval(ReadModel):
    id: int
    event_time: datetime | None
    actor_role: str | None
    actor_id: str | None
    action: str | None
    outcome: str | None


class CaseDetail(CaseSummary):
    parties: list[Party]
    documents: list[Document]
    trade_lines: list[Line]
    discrepancies: list[Finding]
    risk_events: list[Risk]
    approvals: list[Approval]


class CaseList(BaseModel):
    items: list[CaseSummary]
    total: int
    limit: int
    offset: int


class ProductCount(BaseModel):
    product: str | None
    count: int


class DashboardSummary(BaseModel):
    total_cases: int
    synthetic_cases: int
    expected_outcomes: dict[str, int]
    product_distribution: list[ProductCount]
