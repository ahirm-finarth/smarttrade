"""Strict, credential-free provider inputs/results; signals never decide a trade."""

import re
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.examination import Evidence


class CheckStatus(StrEnum):
    CLEAR = "CLEAR"
    POTENTIAL_MATCH = "POTENTIAL_MATCH"
    HIT = "HIT"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    NOT_CHECKED = "NOT_CHECKED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    PROVIDER_ERROR = "PROVIDER_ERROR"


class Category(StrEnum):
    SCREENING = "screening"
    COUNTRY = "country"
    PORT = "port"
    VESSEL = "vessel"
    DUPLICATE = "duplicate"
    GOODS = "goods"
    FAIR_VALUE = "fair_value"


def assert_safe(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            if re.search(r"password|secret|token|authorization|api.?key|credential", key, re.I):
                raise ValueError("Secret metadata is forbidden in provider audit")
            assert_safe(item)
    elif isinstance(value, list):
        for item in value:
            assert_safe(item)
    elif isinstance(value, str) and re.search(
        r"Bearer\s+\S+|github_pat_|ghp_|https?://[^/\s]+:[^/\s]+@", value, re.I
    ):
        raise ValueError("Credential-like data is forbidden in provider audit")


class SafeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    @model_validator(mode="after")
    def safe(self):
        assert_safe(self.model_dump(mode="json"))
        return self


class ProviderInput(SafeModel):
    subject_type: str
    subject: str | None = None
    role: str | None = None
    country: str | None = None
    party_id: int | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    trade: dict[str, Any] = Field(default_factory=dict)


class ReferenceRecord(SafeModel):
    reference_id: str
    reference_type: str
    name: str
    country: str | None = None
    status: str
    note: str


class ProviderResult(SafeModel):
    status: CheckStatus
    reason: str
    matched_records: list[ReferenceRecord] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
    synthetic: bool = True


class RiskProvider(Protocol):
    category: Category
    name: str
    version: str

    def check(self, subject: ProviderInput) -> ProviderResult: ...
    def snapshot(self) -> dict: ...


class ProviderRegistry:
    def __init__(self, providers: list[RiskProvider]):
        self.providers = {p.category: p for p in providers}
        if len(self.providers) != len(providers):
            raise ValueError("Duplicate provider category")

    def get(self, category: Category) -> RiskProvider:
        return self.providers[category]

    def snapshot(self) -> list[dict]:
        result = [self.providers[c].snapshot() for c in sorted(self.providers)]
        assert_safe(result)
        return result
