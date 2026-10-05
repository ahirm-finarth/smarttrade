import pytest
from pydantic import ValidationError

from app.rules import IMPORT, PLAYBOOKS, Rule, Subject, load_rules, validate_rules


def test_playbooks_and_explicit_rule_versions():
    for playbook in PLAYBOOKS:
        rules = load_rules(playbook)
        assert rules and len({r.id for r in rules}) == len(rules)
        assert all(r.version == 1 for r in rules)
    amount = next(r for r in load_rules(IMPORT) if r.id == "DOC-LC-AMOUNT-001")
    assert amount.parameters == {"tolerance_percent": "0", "mode": "equal"}
    assert amount.model_dump(mode="json")["left"]["document_type"] == "LETTER_OF_CREDIT"
    with pytest.raises(ValueError):
        load_rules("Unknown product")
    with pytest.raises(ValueError):
        validate_rules([amount, amount])


@pytest.mark.parametrize(
    "changes",
    [
        {"comparison": "RUN_ARBITRARY_CODE"},
        {"version": 0},
        {"playbooks": ["Unknown"]},
        {"parameters": {"tolerance_percent": "NaN", "mode": "equal"}},
        {"parameters": {"tolerance_percent": "0", "mode": "guess"}},
        {"parameters": {}},
        {"parameters": {"tolerance_percent": "0", "mode": "equal", "code": "x"}},
    ],
)
def test_bad_rule_configuration_is_rejected(changes):
    rule = next(r for r in load_rules(IMPORT) if r.id == "DOC-LC-AMOUNT-001")
    with pytest.raises(ValidationError):
        Rule.model_validate({**rule.model_dump(), **changes})


def test_unknown_extraction_fields_and_presence_wiring_are_rejected():
    with pytest.raises(ValidationError):
        Subject(document_type="LETTER_OF_CREDIT", fields=("made_up",), role="Test")
    amount = next(r for r in load_rules(IMPORT) if r.id == "DOC-LC-AMOUNT-001")
    with pytest.raises(ValidationError):
        Rule.model_validate(
            {**amount.model_dump(), "comparison": "DOCUMENT_PRESENT", "parameters": {}}
        )
