from typing import Literal
from uuid import UUID, uuid4

from pydantic import Field, field_validator, model_validator

from app.integrations.risk.contracts import SafeModel
from app.rules.workflow import Action, TaskType


class TaskActionRequest(SafeModel):
    action: Action
    actor_id: str = Field(min_length=1, max_length=64)
    comment: str = Field(default="", max_length=4000)
    expected_revision: int = Field(ge=1)
    request_id: UUID = Field(default_factory=uuid4)
    target_queue: (
        Literal[TaskType.TRADE, TaskType.COMPLIANCE, TaskType.LEGAL, TaskType.ESCALATION] | None
    ) = None

    @field_validator("comment")
    @classmethod
    def trim(cls, value):
        return value.strip()

    @model_validator(mode="after")
    def rationale(self):
        if self.action != Action.START and len(self.comment) < 3:
            raise ValueError("Action rationale is required")
        if self.target_queue is not None and self.action != Action.ESCALATE:
            raise ValueError("Target queue is only supported for escalation")
        return self


class OverrideRequest(SafeModel):
    actor_id: str = Field(min_length=1, max_length=64)
    reason_code: Literal["ACCEPT_REVIEWED_EXCEPTION"]
    rationale: str = Field(min_length=8, max_length=4000)
    reason_ids: list[int] = Field(min_length=1, max_length=200)
    evidence_reference: str | None = Field(default=None, max_length=255)
    expected_revision: int = Field(ge=1)
    request_id: UUID = Field(default_factory=uuid4)

    @field_validator("rationale")
    @classmethod
    def trim(cls, value):
        if len(value.strip()) < 8:
            raise ValueError("Override rationale is required")
        return value.strip()

    @field_validator("reason_ids")
    @classmethod
    def distinct_positive_ids(cls, value):
        if len(set(value)) != len(value) or any(id < 1 for id in value):
            raise ValueError("Reason IDs must be positive and distinct")
        return value
