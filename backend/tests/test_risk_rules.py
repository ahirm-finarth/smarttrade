import pytest
from pydantic import ValidationError

from app.integrations.risk.contracts import ProviderResult
from app.rules.risk import RULES, RiskRule, interpret, validate_rules


def test_versioned_rule_configuration_and_severity_retained():
    assert len(RULES) == 8
    assert all(
        r.version == 1 and r.severity in {"LOW", "MEDIUM", "HIGH", "CRITICAL"} for r in RULES
    )
    result = ProviderResult(status="POTENTIAL_MATCH", reason="Synthetic test only")
    assert interpret(RULES[0], result)["status"] == "FINDING"
    assert RULES[0].model_dump()["severity"] == "MEDIUM"


@pytest.mark.parametrize(
    "update",
    [{"version": 0}, {"severity": "BLOCK"}, {"handler": "eval"}, {"category": "final_decision"}],
)
def test_invalid_config_rejected(update):
    with pytest.raises(ValidationError):
        RiskRule.model_validate({**RULES[0].model_dump(), **update})


def test_duplicate_ids_and_unknown_handler_fail_safely():
    with pytest.raises(ValueError):
        validate_rules((RULES[0], RULES[0]))
    unknown = RULES[0].model_copy(update={"handler": "arbitrary"})
    assert (
        interpret(unknown, ProviderResult(status="HIT", reason="test"))["status"] == "NOT_CHECKED"
    )


def test_file_duplicate_is_not_financing_event():
    result = ProviderResult(
        status="POTENTIAL_MATCH",
        reason="candidate",
        details={
            "candidates": [{"kind": "EXACT_FILE_DUPLICATE", "financing_status": "NOT_CHECKED"}]
        },
    )
    assert interpret(RULES[4], result)["findings"][0]["finding_type"] == "EXACT_FILE_DUPLICATE"
    assert not interpret(RULES[5], result)["findings"]
