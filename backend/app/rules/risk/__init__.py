"""Typed, versioned policy interprets provider facts; never final trade decisions."""

from typing import Literal

from pydantic import Field

from app.integrations.risk.contracts import Category, CheckStatus, ProviderResult, SafeModel

RULESET_VERSION = "risk-v1"


class RiskRule(SafeModel):
    id: str = Field(pattern="^RISK-[A-Z0-9-]+$")
    version: int = Field(ge=1)
    category: Category
    name: str
    handler: Literal["SIGNAL", "DUPLICATE", "FINANCING_EVENT"]
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    finding_type: str
    trigger_statuses: tuple[CheckStatus, ...] = (
        CheckStatus.POTENTIAL_MATCH,
        CheckStatus.NEEDS_REVIEW,
        CheckStatus.HIT,
    )


RULES = (
    RiskRule(
        id="RISK-SCREEN-001",
        version=1,
        category="screening",
        name="Synthetic party match requires review",
        handler="SIGNAL",
        severity="MEDIUM",
        finding_type="PARTY_SCREENING_REVIEW",
    ),
    RiskRule(
        id="RISK-COUNTRY-001",
        version=1,
        category="country",
        name="Synthetic country policy signal",
        handler="SIGNAL",
        severity="HIGH",
        finding_type="COUNTRY_POLICY_REVIEW",
    ),
    RiskRule(
        id="RISK-PORT-001",
        version=1,
        category="port",
        name="Synthetic route or port policy signal",
        handler="SIGNAL",
        severity="HIGH",
        finding_type="PORT_POLICY_REVIEW",
    ),
    RiskRule(
        id="RISK-VESSEL-001",
        version=1,
        category="vessel",
        name="Synthetic vessel signal requires review",
        handler="SIGNAL",
        severity="MEDIUM",
        finding_type="VESSEL_REVIEW",
    ),
    RiskRule(
        id="RISK-DUP-001",
        version=1,
        category="duplicate",
        name="Cross-case document or invoice candidate",
        handler="DUPLICATE",
        severity="MEDIUM",
        finding_type="DOCUMENT_DUPLICATE_CANDIDATE",
    ),
    RiskRule(
        id="RISK-DUP-FINANCE-001",
        version=1,
        category="duplicate",
        name="Duplicate candidate needs an independent financing event",
        handler="FINANCING_EVENT",
        severity="HIGH",
        finding_type="POTENTIAL_DUPLICATE_FINANCING",
    ),
    RiskRule(
        id="RISK-GOODS-001",
        version=1,
        category="goods",
        name="Explicit synthetic goods policy signal",
        handler="SIGNAL",
        severity="HIGH",
        finding_type="GOODS_POLICY_REVIEW",
    ),
    RiskRule(
        id="RISK-PRICE-001",
        version=1,
        category="fair_value",
        name="Unit price outside explicit synthetic range",
        handler="SIGNAL",
        severity="MEDIUM",
        finding_type="FAIR_VALUE_REVIEW",
    ),
)


def validate_rules(rules: tuple[RiskRule, ...]) -> tuple[RiskRule, ...]:
    if len({r.id for r in rules}) != len(rules):
        raise ValueError("Duplicate risk rule ID")
    return rules


def interpret(rule: RiskRule, result: ProviderResult) -> dict:
    if rule.handler not in {"SIGNAL", "DUPLICATE", "FINANCING_EVENT"}:
        return {"status": "NOT_CHECKED", "reason": "Unknown handler refused", "findings": []}
    if result.status not in rule.trigger_statuses and rule.handler != "FINANCING_EVENT":
        return {"status": result.status, "reason": result.reason, "findings": []}
    if rule.handler == "SIGNAL":
        return {
            "status": "FINDING",
            "reason": result.reason,
            "findings": [{"finding_type": rule.finding_type, "description": result.reason}],
        }
    candidates = result.details.get("candidates", [])
    if rule.handler == "FINANCING_EVENT":
        candidates = [
            c
            for c in candidates
            if c.get("financing_status") == "FINANCED"
            and c.get("financing_evidence", {}).get("event_id")
            and c.get("financing_evidence", {}).get("source")
        ]
    findings = [
        {
            "finding_type": rule.finding_type if rule.handler == "FINANCING_EVENT" else c["kind"],
            "description": result.reason,
            "candidate": c,
        }
        for c in candidates
    ]
    return {
        "status": "FINDING" if findings else "NOT_CHECKED",
        "reason": result.reason if findings else "No independently evidenced financing event",
        "findings": findings,
    }


validate_rules(RULES)
