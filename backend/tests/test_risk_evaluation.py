from app.services.demo_risk_evaluation import score


def test_missing_supported_scope_labels_count_as_misses_and_other_findings_as_false_positive():
    expected = [
        {"reference_id": "a", "case_id": "A", "category": "port", "subject": "Port Azure"},
        {"reference_id": "b", "case_id": "A", "category": "fair_value", "subject": "resin"},
    ]
    detected = [
        {"id": 1, "case_id": "A", "category": "port", "subject": "PORT AZURE"},
        {"id": 2, "case_id": "B", "category": "vessel", "subject": "other"},
    ]
    result = score(expected, detected)
    assert result["true_positives"] == result["false_positives"] == result["false_negatives"] == 1
    assert result["precision"] == result["recall"] == result["f1"] == "0.5000"


def test_wrong_subject_does_not_match_by_category_only():
    result = score(
        [{"case_id": "A", "category": "port", "subject": "Port Azure"}],
        [{"id": 1, "case_id": "A", "category": "port", "subject": "Port Other"}],
    )
    assert result["true_positives"] == 0 and result["false_negatives"] == 1
