import copy

import pytest
from pydantic import ValidationError

from app.rules.decision import POLICY, DecisionCase, DecisionInput, evaluate


def clean_inputs():
    return DecisionInput(
        case=DecisionCase(case_id="UNIT", product_playbook="Import LC"),
        documentary={"id": 1, "status": "CLEAN", "findings": [], "executions": []},
        risk={
            "id": 2,
            "status": "COMPLETED",
            "findings": [],
            "executions": [],
            "checks": [
                {"id": i, "provider_type": c, "status": "CLEAR", "result_json": {"details": {}}}
                for i, c in enumerate(POLICY.mandatory_categories, 1)
            ],
        },
        documentary_current=True,
        risk_current=True,
    )


def test_clean_inputs_pass_without_human_final_outcome():
    result = evaluate(clean_inputs())
    assert result["recommended_decision"] == "PASS"
    assert "final_outcome" not in result


@pytest.mark.parametrize("status", ["NOT_CHECKED", "INSUFFICIENT_DATA", "PROVIDER_ERROR"])
def test_mandatory_unavailable_controls_prevent_pass(status):
    inputs = clean_inputs()
    inputs.risk["checks"][0]["status"] = status
    assert evaluate(inputs)["recommended_decision"] == "REFER"


def test_not_applicable_and_explicit_optional_unchecked_are_distinct():
    inputs = clean_inputs()
    inputs.risk["checks"][0]["status"] = "NOT_APPLICABLE"
    inputs.risk["checks"].append(
        {
            "id": 9,
            "provider_type": "fair_value",
            "status": "NOT_CHECKED",
            "result_json": {"details": {}},
        }
    )
    result = evaluate(inputs)
    assert result["recommended_decision"] == "PASS"
    assert any(r["reason_code"] == "OPTIONAL_CONTROL_UNCHECKED" for r in result["reasons"])
    inputs.risk["checks"].pop(0)
    assert evaluate(inputs)["recommended_decision"] == "REFER"


def test_documentary_and_risk_findings_refer_with_original_ids():
    inputs = clean_inputs()
    inputs.documentary["findings"] = [
        {
            "id": 8,
            "rule_execution_pk": 4,
            "title": "Amount difference",
            "severity": "HIGH",
            "status": "OPEN",
        }
    ]
    inputs.risk["findings"] = [
        {
            "id": 9,
            "provider_check_pk": 2,
            "title": "Vessel review",
            "severity": "MEDIUM",
            "status": "OPEN",
        }
    ]
    result = evaluate(inputs)
    assert result["recommended_decision"] == "REFER"
    assert result["reasons"][0]["documentary_finding_pk"] == 8
    assert result["reasons"][1]["risk_finding_pk"] == 9


def test_incomplete_guarantee_refers_without_inventing_breach_finding():
    inputs = clean_inputs()
    inputs.documentary["status"] = "INCOMPLETE_EXAMINATION"
    inputs.documentary["executions"] = [{"id": i, "status": "NEEDS_REVIEW"} for i in range(6)]
    result = evaluate(inputs)
    assert result["recommended_decision"] == "REFER"
    assert len(result["reasons"]) == 6
    assert {r["reason_code"] for r in result["reasons"]} == {"INCOMPLETE_EXAMINATION"}


@pytest.mark.parametrize("status", ["POTENTIAL_MATCH", "NEEDS_REVIEW", "HIT"])
def test_candidate_or_unconfirmed_hit_is_never_hard_block(status):
    inputs = clean_inputs()
    inputs.risk["checks"][0]["status"] = status
    assert evaluate(inputs)["recommended_decision"] == "REFER"


def test_hard_block_requires_configured_confirmation_and_independent_evidence():
    inputs = clean_inputs()
    check = inputs.risk["checks"][0]
    check.update(
        status="HIT",
        result_json={
            "details": {
                "confirmation": {
                    "confirmed": True,
                    "control": "CONFIRMED_SCREENING_HIT",
                    "evidence_id": "UNIT-HARD-001",
                    "source": "explicit isolated test control",
                }
            }
        },
    )
    original = copy.deepcopy(inputs.model_dump())
    assert evaluate(inputs)["recommended_decision"] == "BLOCK"
    assert inputs.model_dump() == original
    check["result_json"]["details"]["confirmation"].pop("evidence_id")
    assert evaluate(inputs)["recommended_decision"] == "REFER"


@pytest.mark.parametrize("change", ["missing", "failed", "stale"])
def test_missing_failed_or_stale_source_run_prevents_pass(change):
    inputs = clean_inputs().model_dump()
    if change == "missing":
        inputs["documentary"] = None
    elif change == "failed":
        inputs["risk"]["status"] = "FAILED"
    else:
        inputs["documentary_current"] = False
    assert evaluate(DecisionInput.model_validate(inputs))["recommended_decision"] == "REFER"


def test_expected_decision_cannot_enter_typed_runtime_case():
    with pytest.raises(ValidationError):
        DecisionCase(case_id="UNIT", product_playbook="Import LC", expected_decision="PASS")
