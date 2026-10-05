import copy

from app.services.duplicate_trade import duplicate_candidates


def profile(case="A", doc=1, hash="a", **updates):
    p = {
        "case_id": case,
        "document_id": doc,
        "version_id": doc,
        "sha256": hash,
        "evidence": [],
        "values": {
            "invoice_number": "inv-001",
            "seller": "seller",
            "buyer": "buyer",
            "amount": "100",
            "currency": "USD",
            "purchase_order_reference": "po-1",
        },
    }
    p["values"].update(updates)
    return p


def test_exact_hash_is_document_duplicate_not_financing_proof():
    result = duplicate_candidates(profile(), [profile("B", 2)])[0]
    assert result["kind"] == "EXACT_FILE_DUPLICATE"
    assert "sha256" in result["matched_fields"] and result["financing_status"] == "NOT_CHECKED"


def test_strong_identity_candidate_is_explainable_with_different_po():
    result = duplicate_candidates(
        profile(), [profile("B", 2, "b", purchase_order_reference="po-2")]
    )[0]
    assert result["kind"] == "DOCUMENT_DUPLICATE_CANDIDATE"
    assert result["score"] == "0.95" and result["different_fields"] == ["purchase_order_reference"]


def test_partial_candidate_requires_shared_number_seller_and_buyer():
    result = duplicate_candidates(profile(), [profile("B", 2, "b", amount="105")])[0]
    assert result["score"] == "0.80" and "amount" in result["different_fields"]


def test_same_seller_amount_different_invoice_is_not_duplicate():
    assert not duplicate_candidates(profile(), [profile("B", 2, "b", invoice_number="inv-002")])


def test_unrelated_seller_and_self_are_excluded():
    assert not duplicate_candidates(profile(), [profile("B", 2, "b", seller="other")])
    assert not duplicate_candidates(profile(), [profile(), profile("A", 2, "b")])


def test_search_does_not_mutate_profiles():
    p = profile()
    original = copy.deepcopy(p)
    duplicate_candidates(p, [profile("B", 2, "b")])
    assert p == original
