import copy

import pytest
from sqlalchemy.orm import Session

from app.integrations.llm.client import LLMUnavailable
from app.schemas.advisory import AdvisoryRequest
from app.services.exception_advisor import advisory_input, draft_exception_advice
from tests.test_examination_engine import database as database_fixture  # noqa: F401
from tests.test_governed_workflow import SETTINGS, action, clean_decision


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


def test_advisory_distinguishes_resolved_governance_from_original_open_findings(database):
    from app.services.decision_overrides import apply_override
    from tests.test_decision_overrides import override_payload, reviewed_refer

    with Session(database) as s:
        run = reviewed_refer(s)
        run = apply_override(s, SETTINGS, run.id, override_payload(run))
        run = action(s, run, "MAKER_REVIEW", "maker.demo", "SUBMIT_FOR_CHECKER")
        run = action(s, run, "CHECKER_APPROVAL", "checker.demo", "APPROVE")
        inputs = advisory_input(run)
        assert inputs["recommended_decision"] == "REFER"
        assert inputs["governance"]["final_outcome"] == "PASS"
        assert inputs["governance"]["unresolved_reason_ids"] == []
        assert inputs["governance"]["latest_resolutions"]
        assert inputs["governance"]["accepted_exception_reason_ids"]
        assert any(r["status"] == "OPEN" for r in inputs["reasons"])
        assert "rationale" not in str(inputs["governance"])


def test_workflow_change_during_drafting_discards_advisory_without_undoing_action(database):
    from app.services.workflow_controls import WorkflowConflict

    with Session(database) as s:
        run = clean_decision(s)

        class RacingAdvisor:
            def structured(self, messages, schema, max_tokens):
                action(s, run, "MAKER_REVIEW", "maker.demo", "SUBMIT_FOR_CHECKER")
                return response(run)

        with pytest.raises(WorkflowConflict, match="changed while drafting"):
            draft_exception_advice(s, SETTINGS, run.id, AdvisoryRequest(), RacingAdvisor())
        s.refresh(run.workflow)
        assert run.workflow.state == "AWAITING_CHECKER"
        assert not any(e.event_type == "EXCEPTION_SUMMARY_GENERATED" for e in run.events)
