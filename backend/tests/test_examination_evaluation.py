from app.services.demo_examination_evaluation import score_findings


def reference(rule="LC-QTY-001", expected="100 MT", observed="105 MT"):
    return {
        "finding_id": "LABEL",
        "case_id": "CASE",
        "rule_id": rule,
        "expected_value": expected,
        "observed_value": observed,
    }


def finding(id=1, kind="QUANTITY_MISMATCH", expected=None, observed=None):
    return {
        "id": id,
        "case_id": "CASE",
        "finding_type": kind,
        "expected": expected or {"quantity": "100", "unit": "MT"},
        "observed": observed or {"quantity": "105", "unit": "MT"},
    }


def test_quantity_label_accounts_for_both_comparisons_without_hiding_raw_count():
    report = score_findings([reference()], [finding(), finding(2)])
    assert report["true_positives"] == 1
    assert report["detected_raw_findings"] == 2
    assert report["detected_case_families"] == 1
    assert report["additional_matching_comparisons"] == 1
    assert report["false_positives"] == report["false_negatives"] == 0
    assert report["precision"] == report["recall"] == report["f1"] == "1.0000"


def test_wrong_values_are_false_positive_and_missed_reference_not_type_only_match():
    report = score_findings([reference()], [finding(observed={"quantity": "106", "unit": "MT"})])
    assert report["false_positives"] == report["false_negatives"] == 1
    assert report["true_positives"] == 0
    assert report["unmatched_findings"]


def test_missing_reference_finding_is_reported_and_risk_label_excluded():
    report = score_findings([reference(), reference("DOC-INV-REF-001")], [])
    assert report["expected_discrepancies"] == report["false_negatives"] == 1
    assert report["excluded_references"][0]["rule_id"] == "DOC-INV-REF-001"
    assert report["f1"] == "0.0000"


def test_money_dates_and_identifiers_require_actual_values():
    labels = [
        reference("LC-AMOUNT-001", "USD 120,000.00", "USD 126,000.00"),
        reference("LC-SHIP-DATE-001", "On or before 2026-03-15", "2026-03-18"),
        reference("LC-PO-REF-001", "PO-45078", "PO-45087"),
    ]
    actual = [
        finding(
            1,
            "AMOUNT_MISMATCH",
            {"amount": "120000.00", "currency": "USD"},
            {"amount": "126000.00", "currency": "USD"},
        ),
        finding(2, "LATE_SHIPMENT", "2026-03-15", "2026-03-18"),
        finding(3, "PURCHASE_ORDER_MISMATCH", "PO-45078", "PO-45087"),
    ]
    report = score_findings(labels, actual)
    assert report["true_positives"] == 3
    assert report["false_positives"] == report["false_negatives"] == 0
