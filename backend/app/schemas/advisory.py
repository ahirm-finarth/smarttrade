from typing import Literal
from uuid import UUID, uuid4

from pydantic import Field

from app.integrations.risk.contracts import SafeModel


class AdvisoryRequest(SafeModel):
    actor_id: str = Field(default="maker.demo", max_length=64)
    request_id: UUID = Field(default_factory=uuid4)


class IssueGroup(SafeModel):
    label: str = Field(min_length=1, max_length=160)
    reason_ids: list[int] = Field(min_length=1, max_length=40)


class ExceptionAdvice(SafeModel):
    executive_summary: str = Field(min_length=1, max_length=1800)
    grouped_issues: list[IssueGroup] = Field(max_length=20)
    suggested_queue: Literal[
        "TRADE_REVIEW",
        "COMPLIANCE_REVIEW",
        "LEGAL_REVIEW",
        "SUPERVISOR_ESCALATION",
        "MIXED",
        "NONE",
    ]
    draft_reviewer_note: str = Field(max_length=1800)
    draft_information_request: str = Field(max_length=1800)
