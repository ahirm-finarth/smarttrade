"""Supplied synthetic reference table stands in for an external watchlist provider."""

import csv
from difflib import SequenceMatcher
from pathlib import Path

from app.integrations.risk.contracts import (
    Category,
    CheckStatus,
    ProviderInput,
    ProviderResult,
    ReferenceRecord,
)
from app.services.comparisons import normalized_party, normalized_text

REFERENCE_SOURCE = Path(__file__).resolve().parents[4] / "data/raw/reference_screening.csv"


def load_references(path: Path = REFERENCE_SOURCE) -> list[ReferenceRecord]:
    with path.open(newline="", encoding="utf-8-sig") as source:
        return [ReferenceRecord.model_validate(r) for r in csv.DictReader(source)]


class SyntheticLookupProvider:
    version = "synthetic-v1"

    def __init__(self, category: Category, records: list[ReferenceRecord]):
        self.category = category
        self.name = "SYNTHETIC_" + category.upper()
        types = {
            Category.SCREENING: "Fictional counterparty",
            Category.PORT: "Fictional adverse route",
            Category.VESSEL: "Fictional vessel alert",
            Category.COUNTRY: "Fictional country policy",
        }
        self.records = [r for r in records if r.reference_type == types[category]]

    def snapshot(self):
        return {
            "category": self.category,
            "name": self.name,
            "version": self.version,
            "reference_source": "supplied synthetic reference_screening.csv",
            "records": [r.model_dump(mode="json") for r in self.records],
        }

    def check(self, subject: ProviderInput) -> ProviderResult:
        if not subject.subject:
            return ProviderResult(status=CheckStatus.NOT_APPLICABLE, reason="No applicable subject")
        if not self.records and self.category == Category.COUNTRY:
            return ProviderResult(
                status=CheckStatus.NOT_CHECKED,
                reason="No supplied synthetic country-policy reference exists",
            )
        normalize = normalized_party if self.category == Category.SCREENING else normalized_text
        value = normalize(subject.subject)
        exact = [r for r in self.records if normalize(r.name) == value]
        if exact:
            # ZZ is a fictional placeholder, not verified geography or an identity discriminator.
            active = [r for r in exact if r.status in {"REVIEW", "POTENTIAL_MATCH", "HIT"}]
            return ProviderResult(
                status=(
                    CheckStatus.POTENTIAL_MATCH
                    if self.category == Category.SCREENING
                    else CheckStatus.NEEDS_REVIEW
                )
                if active
                else CheckStatus.CLEAR,
                reason="Exact normalized match in supplied demo-only reference table",
                matched_records=exact,
                details={
                    "match_method": "normalized exact",
                    "country_note": "Reference ZZ is fictional; no country identity claim",
                    "reference_scope": "Synthetic signals only, not genuine sanctions",
                },
            )
        if self.category == Category.SCREENING:
            near = [
                r
                for r in self.records
                if SequenceMatcher(None, value, normalize(r.name)).ratio() >= 0.90
                and abs(len(value.split()) - len(normalize(r.name).split())) <= 1
            ]
            if near:
                return ProviderResult(
                    status=CheckStatus.POTENTIAL_MATCH,
                    reason="Conservative name similarity requires analyst validation",
                    matched_records=near,
                    details={"match_method": "SequenceMatcher >=0.90; never confirmed identity"},
                )
        return ProviderResult(
            status=CheckStatus.CLEAR,
            reason="No match within the supplied synthetic reference list; not live screening",
        )


class UnavailableSyntheticProvider(SyntheticLookupProvider):
    """Preserve an auditable check when the reference source cannot be loaded."""

    def __init__(self, category: Category):
        super().__init__(category, [])

    def snapshot(self):
        return {**super().snapshot(), "reference_available": False}

    def check(self, subject: ProviderInput) -> ProviderResult:
        return ProviderResult(
            status=CheckStatus.PROVIDER_ERROR,
            reason="Synthetic reference source unavailable; private diagnostics suppressed",
        )


class SyntheticScreeningProvider(SyntheticLookupProvider):
    def __init__(self, records):
        super().__init__(Category.SCREENING, records)


class SyntheticCountryRiskProvider(SyntheticLookupProvider):
    def __init__(self, records):
        super().__init__(Category.COUNTRY, records)


class SyntheticPortRiskProvider(SyntheticLookupProvider):
    def __init__(self, records):
        super().__init__(Category.PORT, records)


class SyntheticVesselRiskProvider(SyntheticLookupProvider):
    def __init__(self, records):
        super().__init__(Category.VESSEL, records)
