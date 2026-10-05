"""Small typed demo policy; no reference labels, model authority or generic DSL."""

from typing import Literal

from app.integrations.risk.contracts import Category, SafeModel

Recommendation = Literal["PASS", "REFER", "BLOCK"]


class DecisionPolicy(SafeModel):
    version: str = "decision-v1"
    mandatory_categories: tuple[Category, ...] = (
        Category.SCREENING,
        Category.PORT,
        Category.VESSEL,
        Category.DUPLICATE,
    )
    optional_categories: tuple[Category, ...] = (
        Category.COUNTRY,
        Category.GOODS,
        Category.FAIR_VALUE,
    )
    required_approvals: tuple[str, ...] = ("TRADE_MAKER", "TRADE_CHECKER")
    hard_controls: tuple[str, ...] = (
        "CONFIRMED_SCREENING_HIT",
        "CONFIRMED_PROHIBITED_CONDITION",
        "CONFIRMED_DUPLICATE_FINANCING",
    )
    overrideable_codes: tuple[str, ...] = ("DOCUMENTARY_FINDING", "RISK_REVIEW")
    financing_event_control_mandatory: bool = False


POLICY = DecisionPolicy()


class DecisionCase(SafeModel):
    case_id: str
    product_playbook: str | None
    currency: str | None = None
    amount: str | None = None


class DecisionInput(SafeModel):
    case: DecisionCase
    documentary: dict | None
    risk: dict | None
    documentary_current: bool
    risk_current: bool
    policy: DecisionPolicy = POLICY


def evaluate(inputs: DecisionInput) -> dict:
    reasons = []

    def add(
        key,
        code,
        title,
        *,
        impact="REFER",
        severity="MEDIUM",
        status="UNRESOLVED",
        reason_type="CONTROL",
        evidence=None,
        **references,
    ):
        reasons.append(
            {
                "reason_key": key,
                "reason_code": code,
                "title": title,
                "reason_type": reason_type,
                "impact": impact,
                "severity": severity,
                "source_status": status,
                "evidence_json": evidence or {},
                **references,
            }
        )

    doc, risk = inputs.documentary, inputs.risk
    for name, source, current in (
        ("documentary", doc, inputs.documentary_current),
        ("risk", risk, inputs.risk_current),
    ):
        if source is None:
            add(
                name + "-missing",
                "MISSING_SOURCE_RUN",
                f"No {name} source run exists",
                evidence={"source": name},
            )
        elif source["status"] not in (
            {"CLEAN", "DISCREPANCIES_FOUND", "INCOMPLETE_EXAMINATION"}
            if name == "documentary"
            else {"COMPLETED", "PARTIAL"}
        ):
            add(
                name + "-unavailable",
                "SOURCE_RUN_UNAVAILABLE",
                f"{name.capitalize()} source execution is unavailable",
                status=source["status"],
                evidence={"source": name, "run_id": source["id"]},
            )
        elif not current:
            add(
                name + "-stale",
                "STALE_SOURCE_RUN",
                f"{name.capitalize()} source run is stale",
                evidence={"source": name, "run_id": source["id"]},
            )
    if doc:
        for finding in doc["findings"]:
            add(
                f"documentary-{finding['id']}",
                "DOCUMENTARY_FINDING",
                finding["title"],
                reason_type="DOCUMENTARY_FINDING",
                severity=finding["severity"],
                status=finding["status"],
                evidence=finding,
                documentary_finding_pk=finding["id"],
                examination_execution_pk=finding["rule_execution_pk"],
            )
        incomplete = [e for e in doc["executions"] if e["status"] not in {"MATCH", "MISMATCH"}]
        for execution in incomplete:
            add(
                f"incomplete-{execution['id']}",
                "INCOMPLETE_EXAMINATION",
                "Documentary comparison requires source review",
                status=execution["status"],
                reason_type="INCOMPLETE_EXAMINATION",
                evidence=execution,
                examination_execution_pk=execution["id"],
            )
        if doc["status"] == "INCOMPLETE_EXAMINATION" and not incomplete:
            add(
                "incomplete-documentary",
                "INCOMPLETE_EXAMINATION",
                "Documentary examination remains incomplete",
                evidence={"source": "documentary"},
            )
    if risk:
        categories = {c["provider_type"] for c in risk["checks"]}
        for category in inputs.policy.mandatory_categories:
            if category not in categories:
                add(
                    f"missing-{category}",
                    "MISSING_MANDATORY_CONTROL",
                    f"Mandatory {category} control was not executed",
                    evidence={"category": category},
                )
        covered = {f["provider_check_pk"] for f in risk["findings"]}
        for check in risk["checks"]:
            category, status = check["provider_type"], check["status"]
            confirmation = check["result_json"].get("details", {}).get("confirmation", {})
            hard = (
                status == "HIT"
                and confirmation.get("confirmed") is True
                and confirmation.get("control") in inputs.policy.hard_controls
                and confirmation.get("evidence_id")
                and confirmation.get("source")
            )
            if hard:
                add(
                    f"hard-{check['id']}",
                    "CONFIRMED_HARD_BLOCK",
                    "Configured hard control independently confirmed",
                    impact="BLOCK",
                    severity="CRITICAL",
                    status=status,
                    reason_type="HARD_CONTROL",
                    evidence=check,
                    provider_check_pk=check["id"],
                )
            elif (
                status in {"POTENTIAL_MATCH", "NEEDS_REVIEW", "HIT"} and check["id"] not in covered
            ):
                add(
                    f"review-{check['id']}",
                    "RISK_REVIEW",
                    "Provider signal requires human review",
                    status=status,
                    reason_type="RISK_FINDING",
                    evidence=check,
                    provider_check_pk=check["id"],
                )
            elif status not in {
                "CLEAR",
                "NOT_APPLICABLE",
                "POTENTIAL_MATCH",
                "NEEDS_REVIEW",
                "HIT",
            }:
                mandatory = category in inputs.policy.mandatory_categories
                add(
                    f"unchecked-{check['id']}",
                    "MANDATORY_CONTROL_UNAVAILABLE" if mandatory else "OPTIONAL_CONTROL_UNCHECKED",
                    (
                        f"{category.replace('_', ' ').capitalize()} control: "
                        f"{status.lower().replace('_', ' ')}"
                    ),
                    impact="REFER" if mandatory else "INFO",
                    status=status,
                    reason_type="CONTROL_COMPLETENESS",
                    evidence=check,
                    provider_check_pk=check["id"],
                )
        for finding in risk["findings"]:
            add(
                f"risk-{finding['id']}",
                "RISK_REVIEW",
                finding["title"],
                reason_type="RISK_FINDING",
                severity=finding["severity"],
                status=finding["status"],
                evidence=finding,
                risk_finding_pk=finding["id"],
                provider_check_pk=finding["provider_check_pk"],
            )
        for execution in risk["executions"]:
            if (
                execution["rule_id"] == "RISK-DUP-FINANCE-001"
                and execution["status"] == "NOT_CHECKED"
            ):
                mandatory = inputs.policy.financing_event_control_mandatory
                add(
                    f"financing-{execution['id']}",
                    "MANDATORY_CONTROL_UNAVAILABLE" if mandatory else "OPTIONAL_CONTROL_UNCHECKED",
                    "Independent financing-event control remains unchecked",
                    impact="REFER" if mandatory else "INFO",
                    status="NOT_CHECKED",
                    reason_type="CONTROL_COMPLETENESS",
                    evidence=execution,
                    provider_check_pk=execution["provider_check_pk"],
                )
    recommendation = (
        "BLOCK"
        if any(r["impact"] == "BLOCK" for r in reasons)
        else "REFER"
        if any(r["impact"] == "REFER" for r in reasons)
        else "PASS"
    )
    if recommendation == "PASS":
        add(
            "pass-eligible",
            "PASS_REQUIREMENTS_MET",
            "Documentary examination and applicable mandatory demo controls complete",
            impact="INFO",
            severity="LOW",
            status="COMPLETE",
            reason_type="POLICY",
            evidence={"required_approvals": inputs.policy.required_approvals},
        )
    return {"recommended_decision": recommendation, "reasons": reasons}
