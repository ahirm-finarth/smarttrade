import pytest

from app.services.comparisons import (
    compare,
    normalized_identifier,
    normalized_party,
    normalized_text,
)


def money(amount, currency="USD"):
    return {"amount": amount, "currency": currency}


@pytest.mark.parametrize(
    "left,right,status",
    [
        (money("100.00"), money("100"), "MATCH"),
        (money("100"), money("100.01"), "MISMATCH"),
        (money("100"), money("100", "EUR"), "NOT_COMPARABLE"),
        (money("NaN"), money("100"), "NOT_COMPARABLE"),
        (money(100.0), money("100"), "NOT_COMPARABLE"),
    ],
)
def test_decimal_amounts(left, right, status):
    assert compare("AMOUNT_WITHIN_TOLERANCE", left, right).status == status


def test_explicit_amount_policy_and_currency_are_separate():
    assert compare("CURRENCY_EQUAL", money("100"), money("100", "EUR")).status == "MISMATCH"
    assert (
        compare(
            "AMOUNT_WITHIN_TOLERANCE", money("100"), money("101"), {"tolerance_percent": "1"}
        ).status
        == "MATCH"
    )
    assert (
        compare("AMOUNT_WITHIN_TOLERANCE", money("100"), money("90"), {"mode": "at_most"}).status
        == "MATCH"
    )


@pytest.mark.parametrize(
    "left,right,status",
    [
        ({"quantity": "100", "unit": "PCS"}, {"quantity": "100.0", "unit": "PIECES"}, "MATCH"),
        ({"quantity": "100", "unit": "MT"}, {"quantity": "105", "unit": "MT"}, "MISMATCH"),
        ({"quantity": "100", "unit": "MT"}, {"quantity": "100000", "unit": "KG"}, "NOT_COMPARABLE"),
    ],
)
def test_quantities(left, right, status):
    assert compare("QUANTITY_EQUAL", left, right).status == status


@pytest.mark.parametrize(
    "right,status",
    [
        ("2026-03-15", "MATCH"),
        ("2026-03-18", "MISMATCH"),
        ("03/15/2026", "NOT_COMPARABLE"),
        ("2026-02-30", "NOT_COMPARABLE"),
    ],
)
def test_deadline(right, status):
    assert compare("DATE_ON_OR_BEFORE", "2026-03-15", right).status == status


def test_conservative_text_identifier_and_party_normalization():
    assert normalized_text("  Café  – goods ") == normalized_text("cafe\u0301 - GOODS")
    assert normalized_identifier("INV-2026-001") == normalized_identifier("INV 2026 001")
    assert normalized_identifier("A-B") != normalized_identifier("AB")
    assert normalized_identifier("INV-001") != normalized_identifier("INV-1")
    assert normalized_party("ABC Exports Pvt. Ltd.") == normalized_party(
        "ABC EXPORTS Private Limited"
    )
    assert (
        compare("PARTY_NAME_MATCH", "Orchid Biopack Limited", "Orchid Biopackz Limited").status
        == "NEEDS_REVIEW"
    )
    assert compare("PARTY_NAME_MATCH", "Alpha Foods LLC", "Beta Machinery LLC").status == "MISMATCH"
    assert compare("PORT_MATCH", "  Chennai", "CHENNAI ").status == "MATCH"
    assert compare("NORMALIZED_TEXT", "CNC bearings", "CNC wheels").status == "MISMATCH"


@pytest.mark.parametrize(
    "left,right,status",
    [(None, None, "MISSING_BOTH"), (None, "x", "MISSING_LEFT"), ("x", None, "MISSING_RIGHT")],
)
def test_missing_inputs(left, right, status):
    assert compare("NORMALIZED_TEXT", left, right).status == status


def test_required_statement_only_when_explicitly_established():
    params = {"required_text": "statement of breach", "aliases": ["breach statement"]}
    requirement = "Signed demand plus statement of breach"
    assert (
        compare(
            "CONTAINS_REQUIRED_TEXT",
            requirement,
            "Required breach statement intentionally absent",
            params,
        ).status
        == "MISMATCH"
    )
    assert compare("CONTAINS_REQUIRED_TEXT", requirement, None, params).status == "MISSING_RIGHT"
    assert (
        compare("CONTAINS_REQUIRED_TEXT", "Signed demand only", "Statement absent", params).status
        == "NOT_COMPARABLE"
    )
    assert (
        compare(
            "CONTAINS_REQUIRED_TEXT", "No statement of breach required", "Statement absent", params
        ).status
        == "NOT_COMPARABLE"
    )
    assert (
        compare(
            "CONTAINS_REQUIRED_TEXT", requirement, "Please attach breach statement", params
        ).status
        == "NOT_COMPARABLE"
    )
    assert (
        compare(
            "CONTAINS_REQUIRED_TEXT",
            requirement,
            "The contractor breached the contract",
            {**params, "observed_field": "breach_statement"},
        ).status
        == "MATCH"
    )


def test_unknown_comparison_and_document_presence():
    assert compare("ARBITRARY_CODE", "a", "b").status == "NOT_COMPARABLE"
    assert compare("DOCUMENT_PRESENT", True, True).status == "MATCH"
