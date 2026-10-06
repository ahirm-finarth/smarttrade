import copy

import pytest
from sqlalchemy.orm import Session

from app.models.domain import CaseDocument
from app.schemas.workflow import OverrideRequest
from app.services import decision_engine
from app.services.decision_engine import decision_is_current, generate_decision, get_decision
from app.services.decision_overrides import apply_override
from app.services.examination_engine import run_examination
from app.services.risk_orchestration import run_risk_checks
from app.services.workflow_controls import WorkflowConflict
from tests.test_decision_engine import prepared_case
from tests.test_examination_engine import add_document
from tests.test_examination_engine import database as database_fixture  # noqa: F401
from tests.test_governed_workflow import SETTINGS, action, clean_decision


def test_final_pass_becomes_historical_when_new_upstream_run_exists(database):
    with Session(database) as session:
        run = action(
            session, clean_decision(session), "MAKER_REVIEW", "maker.demo", "SUBMIT_FOR_CHECKER"
        )
        run = action(session, run, "CHECKER_APPROVAL", "checker.demo", "APPROVE")
        assert run.workflow.final_outcome == "PASS" and decision_is_current(session, SETTINGS, run)
        snapshot = copy.deepcopy(run.input_snapshot_json)
        run_risk_checks(session, SETTINGS, run.input_snapshot_json["case"]["case_id"])
        old = get_decision(session, run.id)
        assert old.workflow.final_outcome == "PASS" and old.input_snapshot_json == snapshot
        assert not decision_is_current(session, SETTINGS, old)


def test_new_document_version_invalidates_decision_without_waiting_for_source_rerun(database):
    with Session(database) as session:
        case = prepared_case(session)
        run = generate_decision(session, SETTINGS, case.case_id)
        document = session.query(CaseDocument).filter_by(case_pk=case.id).first()
        add_document(session, case, document.latest_run.document_type, {}, document=document)
        assert not decision_is_current(session, SETTINGS, run)


def test_incomplete_evidence_cannot_be_cleared_or_waived_even_after_issue_review(database):
    with Session(database) as session:
        case = prepared_case(session)
        document = session.query(CaseDocument).filter_by(case_pk=case.id).first()
        add_document(session, case, document.latest_run.document_type, {}, document=document)
        run_examination(session, SETTINGS, case.case_id)
        run_risk_checks(session, SETTINGS, case.case_id)
        run = generate_decision(session, SETTINGS, case.case_id)
        reason = next(r for r in run.reasons if r.reason_code == "INCOMPLETE_EXAMINATION")
        with pytest.raises(WorkflowConflict):
            action(session, run, "TRADE_REVIEW", "trade.demo", "CONFIRM_CLEAR")
        run = action(
            session, get_decision(session, run.id), "TRADE_REVIEW", "trade.demo", "CONFIRM_ISSUE"
        )
        with pytest.raises(WorkflowConflict, match="cannot be waived"):
            apply_override(
                session,
                SETTINGS,
                run.id,
                OverrideRequest(
                    actor_id="supervisor.demo",
                    reason_code="ACCEPT_REVIEWED_EXCEPTION",
                    rationale="Synthetic attempt to waive missing evidence",
                    reason_ids=[reason.id],
                    expected_revision=run.workflow.revision,
                ),
            )
        assert get_decision(session, run.id).workflow.final_outcome is None


def test_failed_decision_output_has_no_partial_records(database, monkeypatch):
    with Session(database) as session:
        case = prepared_case(session)

        def fail(*args, **kwargs):
            raise RuntimeError("Synthetic persistence failure")

        monkeypatch.setattr(decision_engine, "create_task", fail)
        run = generate_decision(session, SETTINGS, case.case_id)
        assert run.status == "FAILED" and run.recommended_decision is None
        assert not run.reasons and not run.tasks and run.workflow is None
        assert run.error_message and "Synthetic persistence failure" not in run.error_message
