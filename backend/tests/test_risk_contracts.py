import pytest
from pydantic import ValidationError

from app.integrations.risk.contracts import CheckStatus, ProviderInput, ProviderResult


def test_status_contract_is_not_a_transaction_decision():
    assert "PASS" not in CheckStatus and "BLOCK" not in CheckStatus
    assert ProviderResult(status="NOT_CHECKED", reason="No reference").synthetic
    with pytest.raises(ValidationError):
        ProviderResult(status="REFER", reason="Forbidden final decision")


@pytest.mark.parametrize(
    "details",
    [
        {"authorization": "private"},
        {"nested": {"api_key": "private"}},
        {"endpoint": "https://user:private@example.test"},
        {"note": "Bearer private"},
    ],
)
def test_provider_audit_rejects_credentials(details):
    with pytest.raises(ValidationError):
        ProviderResult(status="CLEAR", reason="test", details=details)


def test_input_has_explicit_identity_and_no_invented_identifier():
    subject = ProviderInput(subject_type="party", subject="ABC Ltd", role="Buyer", country="IN")
    assert subject.party_id is None and not subject.evidence
    with pytest.raises(ValidationError):
        ProviderInput(subject_type="party", expected_decision="BLOCK")
