from decimal import Decimal

import pytest

from app.integrations.pdf.parser import ParsedPage, ParsedPDF
from app.models.documents import ExtractedFact
from app.services.evidence import normalize_and_validate, reconcile_evidence
from app.services.normalization import (
    NormalizationError,
    normalize_boolean,
    normalize_date,
    normalize_money,
    normalize_quantity,
)


def test_money_decimal_date_quantity_boolean():
    assert normalize_money("$100,000 USD") == {"currency": "USD", "amount": "100000.00"}
    assert normalize_money("INR 2,50,00,000") == {"currency": "INR", "amount": "25000000.00"}
    assert normalize_money("EUR 0.10")["amount"] == "0.10"
    assert normalize_date("5 October 2026") == "2026-10-05"
    assert normalize_quantity("1,250 PCS") == {"quantity": "1250", "unit": "PCS"}
    assert normalize_boolean("Partial shipment not allowed") is False
    assert normalize_boolean("Partial shipment allowed") is True


@pytest.mark.parametrize("raw", ["$100", "USD 12,34", "USD nan", "USD 1.234", "USD EUR 1"])
def test_ambiguous_money_is_rejected(raw):
    with pytest.raises(NormalizationError):
        normalize_money(raw)


def test_invalid_dates_and_booleans():
    for date in ("05/10/2026", "2026-02-30"):
        with pytest.raises(NormalizationError):
            normalize_date(date)
    with pytest.raises(NormalizationError):
        normalize_boolean("maybe")


def test_source_match_and_unsupported_fact_flagging():
    page = "Invoice amount\nUSD 85,000\nQuantity\n50 EA"
    assert reconcile_evidence(page, "Invoice amount USD 85,000", "USD 85,000")
    assert not reconcile_evidence(page, "Invoice amount USD 90,000", "USD 90,000")
    assert not reconcile_evidence(page, "Invoice amount USD 85,000", "USD 90,000")
    fact = ExtractedFact(
        field_name="total_amount",
        raw_value="USD 85,000",
        page_number=1,
        source_text="Invoice amount\nUSD 85,000",
        confidence=Decimal("0.98"),
    )
    normalize_and_validate([fact], "COMMERCIAL_INVOICE", ParsedPDF([ParsedPage(1, page, False)]))
    assert fact.normalized_json["amount"] == "85000.00"
    assert fact.evidence_status == "SUPPORTED"
    fact.source_text = "fabricated quotation"
    normalize_and_validate([fact], "COMMERCIAL_INVOICE", ParsedPDF([ParsedPage(1, page, False)]))
    assert fact.evidence_status == "NEEDS_REVIEW"
    assert "could not be matched" in fact.review_reason


def test_native_row_anchor_preserves_original_model_value_and_never_accepts_wrong_amount():
    page = "Amount\nUSD 85,000\nApplicant\nSource Company"
    fact = ExtractedFact(
        field_name="total_amount",
        raw_value="USD 85,000.00",
        page_number=1,
        source_text="Amount",
        confidence=Decimal("0.98"),
    )
    provenance = normalize_and_validate(
        [fact], "COMMERCIAL_INVOICE", ParsedPDF([ParsedPage(1, page, False)])
    )
    assert fact.evidence_status == "SUPPORTED"
    assert fact.raw_value == "USD 85,000"
    assert fact.source_text == "Amount\nUSD 85,000"
    assert provenance["total_amount"]["model_raw_value"] == "USD 85,000.00"
    fact.raw_value, fact.source_text = "USD 90,000.00", "Amount"
    normalize_and_validate([fact], "COMMERCIAL_INVOICE", ParsedPDF([ParsedPage(1, page, False)]))
    assert fact.evidence_status == "NEEDS_REVIEW"
    assert fact.raw_value == "USD 90,000.00"


def test_ambiguous_and_unrelated_native_row_anchors_require_review():
    for page, raw, label in (
        ("Amount\nUSD 1\nAmount\nUSD 1", "USD 1", "Amount"),
        ("Applicant\nSource Company\nBeneficiary\nOther Company", "Other Company", "Applicant"),
        ("Amount\nUSD 1", "USD 1", "Invented label"),
    ):
        fact = ExtractedFact(
            field_name="total_amount",
            raw_value=raw,
            page_number=1,
            source_text=label,
            confidence=Decimal("0.98"),
        )
        normalize_and_validate(
            [fact], "COMMERCIAL_INVOICE", ParsedPDF([ParsedPage(1, page, False)])
        )
        assert fact.evidence_status == "NEEDS_REVIEW"
