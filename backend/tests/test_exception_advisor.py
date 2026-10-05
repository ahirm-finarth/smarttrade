import copy

import pytest
from sqlalchemy.orm import Session

from app.integrations.llm.client import LLMUnavailable
from app.schemas.advisory import AdvisoryRequest
from app.services.exception_advisor import draft_exception_advice
from tests.test_examination_engine import database as database_fixture  # noqa: F401
from tests.test_governed_workflow import SETTINGS, clean_decision


def response(run):
    return {
        "executive_summary": "Synthetic controls complete; maker and checker are still required.",
        "grouped_issues": [
            {"label": "Existing unperformed controls", "reason_ids": [run.reasons[0].id]}
        ],
        "suggested_queue": "NONE",
        "draft_reviewer_note": "Review original controls and submit.",
        "draft_information_request": "Request any missing optional reference inputs.",
    }


class MockAdvisor:
    def __init__(self, output):
        self.output = output

    def structured(self, messages, schema, max_tokens):
        assert max_tokens == 2048
        assert "advisory" in messages[0]["content"]
        return self.output


def test_advisory_is_source_grounded_and_cannot_modify_decision_or_tasks(database):
    with Session(database) as s:
        run = clean_decision(s)
        original = copy.deepcopy(run.input_snapshot_json)
        payload = AdvisoryRequest()
        result = draft_exception_advice(s, SETTINGS, run.id, payload, MockAdvisor(response(run)))
        assert result["advisory"] and result["decision_id"] == run.id
        assert run.recommended_decision == "PASS" and run.workflow.final_outcome is None
        assert run.input_snapshot_json == original and len(run.tasks) == 1
        assert (
            draft_exception_advice(s, SETTINGS, run.id, payload, MockAdvisor({}))["event_id"]
            == result["event_id"]
        )


@pytest.mark.parametrize(
    "change", ["unknown_reason", "decision_authority", "wrong_queue", "secret_metadata"]
)
def test_invalid_advisory_is_rejected_and_never_persisted(database, change):
    with Session(database) as s:
        run = clean_decision(s)
        output = response(run)
        if change == "unknown_reason":
            output["grouped_issues"][0]["reason_ids"] = [999999]
        elif change == "decision_authority":
            output["recommended_decision"] = "BLOCK"
        elif change == "wrong_queue":
            output["suggested_queue"] = "LEGAL_REVIEW"
        else:
            output["authorization"] = "private-data"
        with pytest.raises(LLMUnavailable):
            draft_exception_advice(s, SETTINGS, run.id, AdvisoryRequest(), MockAdvisor(output))
        assert not any(e.event_type == "EXCEPTION_SUMMARY_GENERATED" for e in run.events)
        assert run.workflow.final_outcome is None
