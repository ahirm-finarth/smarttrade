from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.cases import ReadModel


class StartRiskRun(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID = Field(default_factory=uuid4)


class RiskSummary(ReadModel):
    id: int
    case_pk: int
    case_id: str = ""
    run_number: int
    ruleset_version: str
    provider_set: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    error_message: str | None
    input_fingerprint: str
    summary_json: dict[str, Any]


class Check(ReadModel):
    id: int
    risk_run_pk: int
    provider_type: str
    provider_name: str
    provider_version: str
    status: str
    input_json: dict[str, Any]
    result_json: dict[str, Any]
    started_at: datetime
    completed_at: datetime | None


class RiskExecution(ReadModel):
    id: int
    risk_run_pk: int
    provider_check_pk: int
    rule_id: str
    rule_version: int
    status: str
    rule_snapshot_json: dict[str, Any]
    input_json: dict[str, Any]
    output_json: dict[str, Any]


class Finding(ReadModel):
    id: int
    risk_run_pk: int
    provider_check_pk: int
    rule_execution_pk: int
    finding_type: str
    category: str
    title: str
    description: str
    severity: str
    rule_id: str
    rule_version: int
    status: str
    subject_type: str
    subject_value: str
    evidence_json: dict[str, Any]
    created_at: datetime


class RiskDetail(BaseModel):
    run: RiskSummary
    checks: list[Check]
    executions: list[RiskExecution]
    findings: list[Finding]
    inputs_current: bool
    synthetic: bool = True
