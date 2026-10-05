import copy
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.services.decision_engine import decision_is_current, generate_decision, get_decision
from app.services.examination_engine import run_examination
from app.services.risk_orchestration import run_risk_checks
from tests.test_examination_engine import database as database_fixture  # noqa: F401
from tests.test_examination_engine import import_case
from tests.test_risk_orchestration import risk_case


def prepared_case(session, risk=False):
    case = risk_case(session) if risk else import_case(session)
    settings = Settings(_env_file=None)
    run_examination(session, settings, case.case_id)
    run_risk_checks(session, settings, case.case_id)
    return case


def test_clean_decision_snapshots_exact_sources_and_requires_maker(database):
    with Session(database) as s:
        case = prepared_case(s)
        run = generate_decision(s, Settings(_env_file=None), case.case_id)
        assert run.status == "COMPLETED" and run.recommended_decision == "PASS"
        assert run.examination_run_pk and run.risk_run_pk
        assert run.workflow.state == "AWAITING_MAKER" and run.workflow.final_outcome is None
        assert run.tasks[0].task_type == "MAKER_REVIEW"
        assert any(r.reason_code == "OPTIONAL_CONTROL_UNCHECKED" for r in run.reasons)
        assert "expected_decision" not in str(run.input_snapshot_json)


def test_risk_decision_routes_actual_findings_and_preserves_history(database):
    with Session(database) as s:
        case = prepared_case(s, risk=True)
        settings = Settings(_env_file=None)
        key = str(uuid4())
        first = generate_decision(s, settings, case.case_id, key)
        snapshot = copy.deepcopy(first.input_snapshot_json)
        assert first.recommended_decision == "REFER"
        assert {t.task_type for t in first.tasks} == {"COMPLIANCE_REVIEW", "TRADE_REVIEW"}
        assert generate_decision(s, settings, case.case_id, key).id == first.id
        assert decision_is_current(s, settings, first)
        run_risk_checks(s, settings, case.case_id)
        assert not decision_is_current(s, settings, first)
        second = generate_decision(s, settings, case.case_id)
        assert second.id != first.id
        old = get_decision(s, first.id)
        assert old.input_snapshot_json == snapshot and old.recommended_decision == "REFER"
        assert old.tasks[0].status == "CANCELLED"
        assert any(e.event_type == "DECISION_SUPERSEDED" for e in old.events)


def test_missing_runs_refer_with_tasks_not_fake_findings(database):
    with Session(database) as s:
        case = import_case(s)
        run = generate_decision(s, Settings(_env_file=None), case.case_id)
        assert run.recommended_decision == "REFER"
        assert {r.reason_code for r in run.reasons} == {"MISSING_SOURCE_RUN"}
        assert run.examination_run_pk is None and run.risk_run_pk is None
