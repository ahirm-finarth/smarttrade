from app.services.demo_decision_evaluation import score


def test_metrics_measure_actual_predictions_and_do_not_imply_block_coverage():
    report = score(
        [
            {"case_id": "a", "expected": "PASS", "recommended": "PASS"},
            {"case_id": "b", "expected": "REFER", "recommended": "PASS"},
            {"case_id": "c", "expected": "REFER", "recommended": "REFER"},
        ]
    )
    assert report["accuracy"] == 2 / 3
    assert report["classes"]["PASS"]["precision"] == 0.5
    assert report["classes"]["REFER"]["recall"] == 0.5
    assert report["classes"]["BLOCK"]["support"] == 0
    assert report["classes"]["BLOCK"]["precision"] is None


def test_missing_recommendation_is_a_miss_and_empty_evaluation_has_no_accuracy():
    assert score([{"expected": "REFER", "recommended": None}])["correct"] == 0
    assert score([])["accuracy"] is None
