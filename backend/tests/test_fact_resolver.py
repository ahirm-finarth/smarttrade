from decimal import Decimal

from app.rules import Subject
from app.services.fact_resolver import resolve


def corpus(*facts, status="COMPLETED", classification="0.99"):
    return {
        "case_id": "TEST",
        "documents": [
            {
                "document_type": "LETTER_OF_CREDIT",
                "status": status,
                "classification_confidence": classification,
                "facts": [
                    {
                        "fact_id": index,
                        "field_name": name,
                        "evidence_status": "SUPPORTED",
                        "source_verified": True,
                        "confidence": confidence,
                        "normalized_value": value,
                        "comparison_value": value,
                    }
                    for index, (name, value, confidence) in enumerate(facts, 1)
                ],
            }
        ],
    }


def test_resolution_missing_review_and_latest_failure():
    role = Subject(document_type="LETTER_OF_CREDIT", fields=("amount",), role="Governing amount")
    assert resolve(corpus(), role, Decimal("0.85")).state == "MISSING"
    assert resolve(corpus(("amount", {}, "0.7")), role, Decimal("0.85")).state == "NEEDS_REVIEW"
    assert (
        resolve(corpus(("amount", {}, "0.99"), status="FAILED"), role, Decimal("0.85")).state
        == "NEEDS_REVIEW"
    )
    assert (
        resolve(corpus(("amount", {}, "0.99"), classification="0.6"), role, Decimal("0.85")).state
        == "NEEDS_REVIEW"
    )


def test_multiple_current_documents_do_not_choose_arbitrarily():
    role = Subject(document_type="LETTER_OF_CREDIT", fields=("amount",), role="Amount")
    data = corpus(("amount", {}, "0.99"))
    data["documents"] *= 2
    assert resolve(data, role, Decimal("0.85")).state == "NEEDS_REVIEW"


def test_route_derivation_retains_actual_fact_and_full_value():
    role = Subject(
        document_type="LETTER_OF_CREDIT",
        fields=("port_of_loading", "route"),
        role="Loading port",
        route_part="loading",
    )
    data = corpus(("route", "Port Lumen / Port Azure", "0.99"))
    result = resolve(data, role, Decimal("0.85"))
    assert result.state == "READY"
    assert result.evidence["field_name"] == "route"
    assert result.evidence["normalized_value"] == "Port Lumen / Port Azure"
    assert result.evidence["comparison_value"] == "Port Lumen"
    assert (
        resolve(corpus(("route", "A / B / C", "0.99")), role, Decimal("0.85")).state
        == "NOT_COMPARABLE"
    )


def test_unsupported_source_never_becomes_comparable():
    role = Subject(document_type="LETTER_OF_CREDIT", fields=("amount",), role="Amount")
    data = corpus(("amount", {}, "0.99"))
    data["documents"][0]["facts"][0]["source_verified"] = False
    assert resolve(data, role, Decimal("0.85")).state == "NEEDS_REVIEW"
