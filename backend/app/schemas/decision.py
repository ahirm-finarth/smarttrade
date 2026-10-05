from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.rules.workflow import DemoActor
from app.schemas.cases import ReadModel


class StartDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID = Field(default_factory=uuid4)


class DecisionSummary(ReadModel):
    id: int
    case_pk: int
    case_id: str = ""
    run_number: int
    examination_run_pk: int | None
    risk_run_pk: int | None
    ruleset_version: str
    status: str
    recommended_decision: str | None
    input_fingerprint: str
    summary_json: dict[str, Any]
    created_at: datetime
    completed_at: datetime | None
    error_message: str | None


class Reason(ReadModel):
    id: int
    decision_run_pk: int
    reason_type: str
    reason_code: str
    impact: str
    severity: str
    source_status: str
    title: str
    route_to: str | None
    documentary_finding_pk: int | None
    risk_finding_pk: int | None
    examination_execution_pk: int | None
    provider_check_pk: int | None
    evidence_json: dict[str, Any]
    created_at: datetime


class Workflow(ReadModel):
    id: int
    decision_run_pk: int
    state: str
    final_outcome: str | None
    maker_actor_id: str | None
    checker_actor_id: str | None
    revision: int
    finalized_at: datetime | None
    updated_at: datetime


class Task(ReadModel):
    id: int
    decision_run_pk: int
    task_type: str
    assigned_role: str
    assigned_actor_id: str | None
    status: str
    priority: str
    title: str
    description: str
    reason_ids_json: list[int]
    resolution: str | None
    created_at: datetime
    assigned_at: datetime | None
    completed_at: datetime | None
    available_actions: list[str] = Field(default_factory=list)


class Event(ReadModel):
    id: int
    decision_run_pk: int
    task_pk: int | None
    request_id: str | None
    event_type: str
    actor_id: str
    actor_role: str
    comment: str
    metadata_json: dict[str, Any]
    created_at: datetime


class Override(ReadModel):
    id: int
    decision_run_pk: int
    workflow_event_pk: int
    actor_id: str
    actor_role: str
    from_decision: str
    to_decision: str
    reason_code: str
    rationale: str
    reason_ids_json: list[int]
    evidence_reference: str | None
    previous_outcome: str | None
    created_at: datetime


class Resolution(ReadModel):
    id: int
    decision_reason_pk: int
    task_pk: int
    workflow_event_pk: int
    actor_id: str
    actor_role: str
    resolution: str
    rationale: str
    created_at: datetime


class DecisionDetail(BaseModel):
    run: DecisionSummary
    input_snapshot: dict[str, Any]
    reasons: list[Reason]
    workflow: Workflow | None
    tasks: list[Task]
    events: list[Event]
    overrides: list[Override]
    resolutions: list[Resolution]
    inputs_current: bool
    effective_final_outcome: str | None
    unresolved_reason_ids: list[int]
    maker_actor_ids: list[str]
    demo_actor: DemoActor
    demo_only: bool = True


class TaskDetail(BaseModel):
    task: Task
    decision: DecisionSummary
    workflow: Workflow | None
    inputs_current: bool


class AuditEntry(BaseModel):
    id: str
    timestamp: datetime
    event_type: str
    actor_id: str
    actor_role: str
    summary: str
    source_url: str
    source_id: int
    detail: dict[str, Any] = Field(default_factory=dict)
