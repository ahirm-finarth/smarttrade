from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.rules.workflow import Action
from app.schemas.workflow import TaskActionRequest
from app.services.decision_engine import generate_decision, get_decision
from app.services.governed_workflow import act_on_task
from app.services.risk_orchestration import run_risk_checks
from app.services.workflow_controls import WorkflowConflict, WorkflowForbidden
from tests.test_decision_engine import prepared_case
from tests.test_examination_engine import database as database_fixture  # noqa: F401

SETTINGS = Settings(_env_file=None)


def action(session, run, kind, actor, name, **kwargs):
    task = next(t for t in run.tasks if t.task_type == kind and t.status in {"OPEN", "IN_PROGRESS"})
    payload = TaskActionRequest(
        action=name,
        actor_id=actor,
        comment=kwargs.pop("comment", "Explicit synthetic workflow review"),
        expected_revision=run.workflow.revision,
        **kwargs,
    )
    return act_on_task(session, SETTINGS, task.id, payload)


def clean_decision(session):
    case = prepared_case(session)
    return generate_decision(session, SETTINGS, case.case_id)


def test_pass_is_only_final_after_distinct_maker_checker_and_audit(database):
    with Session(database) as s:
        run = clean_decision(s)
        assert run.recommended_decision == "PASS" and run.workflow.final_outcome is None
        run = action(s, run, "MAKER_REVIEW", "maker.demo", Action.SUBMIT)
        assert run.workflow.state == "AWAITING_CHECKER" and run.workflow.final_outcome is None
        run = action(s, run, "CHECKER_APPROVAL", "checker.demo", Action.APPROVE)
        assert run.workflow.final_outcome == "PASS" and run.workflow.state == "APPROVED"
        assert {e.event_type for e in run.events} >= {
            "DECISION_GENERATED",
            "TASK_CREATED",
            "MAKER_SUBMITTED",
            "CHECKER_APPROVED",
            "FINAL_PASS",
        }
        assert run.recommended_decision == "PASS"


def test_dual_role_actor_cannot_check_own_maker_submission(database):
    with Session(database) as s:
        run = action(s, clean_decision(s), "MAKER_REVIEW", "dual.demo", Action.SUBMIT)
        with pytest.raises(WorkflowForbidden, match="Segregation"):
            action(s, run, "CHECKER_APPROVAL", "dual.demo", Action.APPROVE)
        run = get_decision(s, run.id)
        assert run.workflow.final_outcome is None
        assert (
            action(
                s, run, "CHECKER_APPROVAL", "checker.demo", Action.APPROVE
            ).workflow.final_outcome
            == "PASS"
        )


def test_checker_return_requires_new_maker_and_preserves_prior_makers_for_sod(database):
    with Session(database) as s:
        run = action(s, clean_decision(s), "MAKER_REVIEW", "dual.demo", Action.SUBMIT)
        run = action(s, run, "CHECKER_APPROVAL", "checker.demo", Action.RETURN)
        assert run.workflow.state == "AWAITING_MAKER" and run.workflow.maker_actor_id is None
        run = action(s, run, "MAKER_REVIEW", "maker.demo", Action.SUBMIT)
        with pytest.raises(WorkflowForbidden, match="Segregation"):
            action(s, run, "CHECKER_APPROVAL", "dual.demo", Action.APPROVE)


def test_unknown_or_wrong_role_and_invalid_transition_rejected(database):
    with Session(database) as s:
        run = clean_decision(s)
        for actor in ("unknown.demo", "checker.demo"):
            with pytest.raises(WorkflowForbidden):
                action(s, run, "MAKER_REVIEW", actor, Action.SUBMIT)
        with pytest.raises(WorkflowConflict):
            action(s, run, "MAKER_REVIEW", "maker.demo", Action.APPROVE)
        assert get_decision(s, run.id).workflow.final_outcome is None


def test_repeated_command_is_idempotent_and_wrong_revision_is_conflict(database):
    with Session(database) as s:
        run = clean_decision(s)
        task = run.tasks[0]
        payload = TaskActionRequest(
            action="SUBMIT_FOR_CHECKER",
            actor_id="maker.demo",
            comment="Reviewed synthetic documents",
            expected_revision=1,
            request_id=uuid4(),
        )
        first = act_on_task(s, SETTINGS, task.id, payload)
        original_events = len(first.events)
        second = act_on_task(s, SETTINGS, task.id, payload)
        assert len(second.events) == original_events
        checker = next(t for t in second.tasks if t.task_type == "CHECKER_APPROVAL")
        with pytest.raises(WorkflowConflict, match="changed"):
            act_on_task(
                s,
                SETTINGS,
                checker.id,
                TaskActionRequest(
                    action="APPROVE",
                    actor_id="checker.demo",
                    comment="Checked",
                    expected_revision=1,
                ),
            )


def test_new_source_run_blocks_old_final_approval(database):
    with Session(database) as s:
        run = action(s, clean_decision(s), "MAKER_REVIEW", "maker.demo", Action.SUBMIT)
        case_id = run.input_snapshot_json["case"]["case_id"]
        run_risk_checks(s, SETTINGS, case_id)
        with pytest.raises(WorkflowConflict, match="stale"):
            action(s, run, "CHECKER_APPROVAL", "checker.demo", Action.APPROVE)
        assert get_decision(s, run.id).workflow.final_outcome is None


def test_information_request_reopens_parent_without_source_resolution(database):
    with Session(database) as s:
        run = action(s, clean_decision(s), "MAKER_REVIEW", "maker.demo", Action.INFORMATION)
        assert run.workflow.state == "NEEDS_INFORMATION"
        run = action(s, run, "REQUEST_INFORMATION", "maker.demo", Action.PROVIDED)
        assert run.workflow.state == "AWAITING_MAKER"
        assert any(e.event_type == "INFORMATION_PROVIDED" for e in run.events)
        assert run.workflow.final_outcome is None


def test_refer_routes_specialists_and_rerouting_is_audited(database):
    with Session(database) as s:
        case = prepared_case(s, risk=True)
        run = generate_decision(s, SETTINGS, case.case_id)
        run = action(s, run, "COMPLIANCE_REVIEW", "compliance.demo", Action.CLEAR)
        assert len(run.resolutions) == 3 and run.recommended_decision == "REFER"
        run = action(
            s, run, "TRADE_REVIEW", "trade.demo", Action.ESCALATE, target_queue="LEGAL_REVIEW"
        )
        assert any(t.task_type == "LEGAL_REVIEW" and t.status == "OPEN" for t in run.tasks)
        assert any(e.metadata_json.get("target_queue") == "LEGAL_REVIEW" for e in run.events)
        with pytest.raises(WorkflowConflict):
            action(s, run, "LEGAL_REVIEW", "legal.demo", Action.CLEAR)
        run = action(s, run, "LEGAL_REVIEW", "legal.demo", Action.ISSUE)
        assert run.workflow.state == "REFERRED" and run.workflow.final_outcome is None


def test_rejection_is_human_outcome_without_rewriting_recommendation(database):
    with Session(database) as s:
        run = action(s, clean_decision(s), "MAKER_REVIEW", "maker.demo", Action.REJECT)
        assert run.recommended_decision == "PASS" and run.workflow.final_outcome == "REJECT"
        assert run.workflow.state == "REJECTED"


def test_required_rationale_and_client_role_claim_are_schema_rejected():
    with pytest.raises(ValidationError):
        TaskActionRequest(
            action="APPROVE", actor_id="checker.demo", comment="  ", expected_revision=1
        )
    with pytest.raises(ValidationError):
        TaskActionRequest(
            action="APPROVE",
            actor_id="maker.demo",
            comment="Valid review",
            expected_revision=1,
            actor_role="TRADE_CHECKER",
        )
