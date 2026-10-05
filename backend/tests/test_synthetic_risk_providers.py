import pytest

from app.integrations.risk.contracts import ProviderInput
from app.integrations.risk.synthetic import (
    SyntheticCountryRiskProvider,
    SyntheticPortRiskProvider,
    SyntheticScreeningProvider,
    SyntheticVesselRiskProvider,
    load_references,
)


@pytest.mark.parametrize(
    "provider,subject,status",
    [
        (SyntheticScreeningProvider, " Vesper Commodities FZE ", "POTENTIAL_MATCH"),
        (SyntheticScreeningProvider, "Asteron Engineering Private Limited", "CLEAR"),
        (SyntheticPortRiskProvider, "PORT AZURE", "NEEDS_REVIEW"),
        (SyntheticPortRiskProvider, "Hamburg", "CLEAR"),
        (SyntheticVesselRiskProvider, "MV Meridian Halo", "NEEDS_REVIEW"),
        (SyntheticVesselRiskProvider, "MV Lumen Star", "CLEAR"),
        (SyntheticCountryRiskProvider, "IN", "NOT_CHECKED"),
        (SyntheticVesselRiskProvider, None, "NOT_APPLICABLE"),
    ],
)
def test_supplied_mock_provider_lookups(provider, subject, status):
    p = provider(load_references())
    result = p.check(ProviderInput(subject_type="test", subject=subject))
    assert result.status == status and result.synthetic
    assert p.name.startswith("SYNTHETIC_") and p.snapshot()["version"]


def test_name_extension_does_not_become_confirmed_identity():
    result = SyntheticScreeningProvider(load_references()).check(
        ProviderInput(subject_type="party", subject="Vesper Commodities International Holdings")
    )
    assert result.status == "CLEAR"


def test_reference_snapshot_retains_original_mock_note():
    p = SyntheticPortRiskProvider(load_references())
    result = p.check(ProviderInput(subject_type="port", subject="Port Azure"))
    assert result.matched_records[0].reference_id == "DEMO-SCR-001"
    assert "demo-only" in result.matched_records[0].note
