import copy

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.integrations.risk.contracts import ProviderResult
from app.integrations.risk.synthetic import SyntheticScreeningProvider, load_references
from app.schemas.workflow import OverrideRequest
from app.services import risk_orchestration
from app.services.decision_engine import decision_is_current, generate_decision, get_decision
from app.services.decision_overrides import apply_override
from app.services.duplicate_trade import invoice_profiles, load_current_corpora
from app.services.risk_orchestration import default_registry, run_risk_checks
from app.services.workflow_controls import WorkflowConflict, WorkflowForbidden
from tests.test_decision_engine import prepared_case
from tests.test_examination_engine import database as database_fixture  # noqa: F401
from tests.test_governed_workflow import SETTINGS, action


def reviewed_refer(session):
    case = prepared_case(session, risk=True)
    run = generate_decision(session, SETTINGS, case.case_id)
    run = action(session, run, "COMPLIANCE_REVIEW", "compliance.demo", "CONFIRM_CLEAR")
    return action(session, run, "TRADE_REVIEW", "trade.demo", "CONFIRM_ISSUE")


def override_payload(run, actor="supervisor.demo"):
    return OverrideRequest(
        actor_id=actor,
        reason_code="ACCEPT_REVIEWED_EXCEPTION",
        rationale="Explicit synthetic acceptance of reviewed documentary exceptions",
        reason_ids=[r.id for r in run.reasons if r.reason_code == "DOCUMENTARY_FINDING"],
        expected_revision=run.workflow.revision,
    )


def test_authorized_refer_override_retains_system_result_and_requires_maker_checker(database):
    with Session(database) as s:
        run = reviewed_refer(s)
        snapshot = copy.deepcopy(run.input_snapshot_json)
        payload = override_payload(run)
        run = apply_override(s, SETTINGS, run.id, payload)
        assert run.recommended_decision == "REFER" and run.workflow.final_outcome is None
        assert run.workflow.state == "AWAITING_MAKER"
        assert len(run.overrides) == 1 and run.overrides[0].rationale == payload.rationale
        assert (
            apply_override(s, SETTINGS, run.id, payload).workflow.revision == run.workflow.revision
        )
        run = action(s, run, "MAKER_REVIEW", "maker.demo", "SUBMIT_FOR_CHECKER")
        run = action(s, run, "CHECKER_APPROVAL", "checker.demo", "APPROVE")
        assert run.workflow.final_outcome == "PASS" and run.recommended_decision == "REFER"
        assert run.input_snapshot_json == snapshot and len(run.overrides) == 1


def test_unauthorized_or_unreviewed_override_rejected_without_mutation(database):
    with Session(database) as s:
        case = prepared_case(s, risk=True)
        run = generate_decision(s, SETTINGS, case.case_id)
        with pytest.raises(WorkflowForbidden):
            apply_override(s, SETTINGS, run.id, override_payload(run, "maker.demo"))
        with pytest.raises(WorkflowConflict, match="specialist"):
            apply_override(s, SETTINGS, run.id, override_payload(run))
        assert not get_decision(s, run.id).overrides


def test_override_requires_rationale_and_cannot_choose_a_client_final_outcome():
    common = {
        "actor_id": "supervisor.demo",
        "reason_code": "ACCEPT_REVIEWED_EXCEPTION",
        "reason_ids": [1],
        "expected_revision": 1,
    }
    for extra in ({"rationale": " "}, {"rationale": "Valid rationale", "to_decision": "PASS"}):
        with pytest.raises(ValidationError):
            OverrideRequest(**common, **extra)


def hard_decision(session, monkeypatch):
    class ConfirmedControl(SyntheticScreeningProvider):
        version = "isolated-confirmed-v1"

        def check(self, subject):
            if not subject.subject:
                return super().check(subject)
            return ProviderResult(
                status="HIT",
                reason="Isolated confirmed hard-control test",
                details={
                    "confirmation": {
                        "confirmed": True,
                        "control": "CONFIRMED_SCREENING_HIT",
                        "evidence_id": "UNIT-HARD-001",
                        "source": "explicit isolated fixture",
                    }
                },
            )

    case = prepared_case(session, risk=True)
    registry = default_registry(
        invoice_profiles(load_current_corpora(session), SETTINGS.examination_min_confidence)
    )
    registry.providers["screening"] = ConfirmedControl(load_references())
    monkeypatch.setattr(risk_orchestration, "default_registry", lambda profiles: registry)
    run_risk_checks(session, SETTINGS, case.case_id, registry=registry)
    return generate_decision(session, SETTINGS, case.case_id)


def test_hard_block_cannot_be_overridden_by_normal_or_supervisor_roles(database, monkeypatch):
    with Session(database) as s:
        run = hard_decision(s, monkeypatch)
        assert run.recommended_decision == "BLOCK" and run.workflow.state == "BLOCKED"
        assert decision_is_current(s, SETTINGS, run)
        for actor in ("maker.demo", "checker.demo", "supervisor.demo"):
            payload = OverrideRequest(
                actor_id=actor,
                reason_code="ACCEPT_REVIEWED_EXCEPTION",
                rationale="Attempted hard-control override",
                reason_ids=[run.reasons[0].id],
                expected_revision=run.workflow.revision,
            )
            with pytest.raises((WorkflowForbidden, WorkflowConflict)):
                apply_override(s, SETTINGS, run.id, payload)
        assert get_decision(s, run.id).workflow.final_outcome is None


def test_only_supervisor_can_acknowledge_block_and_it_never_becomes_pass(database, monkeypatch):
    with Session(database) as s:
        run = hard_decision(s, monkeypatch)
        with pytest.raises(WorkflowForbidden):
            action(s, run, "SUPERVISOR_ESCALATION", "checker.demo", "ACKNOWLEDGE_BLOCK")
        run = action(s, run, "SUPERVISOR_ESCALATION", "supervisor.demo", "ACKNOWLEDGE_BLOCK")
        assert run.workflow.state == "BLOCKED" and run.workflow.final_outcome == "BLOCK"
        assert run.recommended_decision == "BLOCK" and not run.overrides
