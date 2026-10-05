from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.rules import Rule
from app.schemas.cases import ReadModel


class StartExamination(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID = Field(default_factory=uuid4)


class Evidence(BaseModel):
    fact_id: int | None
    case_id: str
    document_id: int
    document_version_id: int
    version_number: int
    processing_run_id: int
    processing_run_number: int
    filename: str
    document_type: str
    field_name: str
    role: str = "Extracted field"
    raw_value: str
    normalized_value: Any
    comparison_value: Any
    page_number: int = Field(ge=1)
    source_text: str
    confidence: Decimal
    evidence_status: str
    source_verified: bool
    review_reason: str | None = None
    derivation: str | None = None


class ResolvedSubject(BaseModel):
    state: str
    reason: str
    evidence: Evidence | None
    candidate_fact_ids: list[int]


class ExecutionInputs(BaseModel):
    expected: ResolvedSubject
    observed: ResolvedSubject


class Execution(ReadModel):
    id: int
    examination_run_pk: int
    rule_id: str
    rule_version: int
    comparison_type: str
    status: str
    rule_snapshot_json: Rule
    input_json: ExecutionInputs
    output_json: dict[str, Any]
    created_at: datetime


class Finding(ReadModel):
    id: int
    examination_run_pk: int
    rule_execution_pk: int
    finding_type: str
    title: str
    description: str
    severity: str
    rule_id: str
    rule_version: int
    status: str
    expected_json: Evidence
    observed_json: Evidence
    created_at: datetime


class Relation(ReadModel):
    id: int
    examination_run_pk: int
    rule_execution_pk: int
    source_fact_pk: int
    target_fact_pk: int
    relation_type: str
    comparison_type: str
    status: str
    confidence: Decimal
    expected: Evidence | None = None
    observed: Evidence | None = None


class ExaminationSummary(ReadModel):
    id: int
    case_pk: int
    case_id: str = ""
    run_number: int
    playbook: str
    ruleset_version: str
    input_fingerprint: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    error_message: str | None
    summary_json: dict[str, Any]


class ExaminationDetail(BaseModel):
    run: ExaminationSummary
    executions: list[Execution]
    findings: list[Finding]
    relations: list[Relation]
    inputs_current: bool


class CurrentCaseEvidence(BaseModel):
    case_id: str
    documents: list[dict[str, Any]]
    facts: list[Evidence]
    confidence_threshold: Decimal
