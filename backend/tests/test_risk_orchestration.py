import copy
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.integrations.risk.contracts import ProviderRegistry
from app.integrations.risk.synthetic import SyntheticScreeningProvider, load_references
from app.models.domain import CaseDocument, CaseParty
from app.models.risk import RiskRun
from app.services.risk_orchestration import get_risk_run, risk_inputs_current, run_risk_checks
from tests.test_examination_engine import add_document, import_case
from tests.test_examination_engine import database as database_fixture  # noqa: F401


def risk_case(session):
    case = import_case(session)
    session.add(
        CaseParty(
            case_pk=case.id,
            source_key="unit-party",
            party_role="Beneficiary",
            party_name="Vesper Commodities FZE",
            country="AE",
            screening_status="CLEAR",
        )
    )
    session.commit()
    doc = session.scalar(select(CaseDocument).where(CaseDocument.file_name == "BILL_OF_LADING.pdf"))
    add_document(
        session,
        case,
        "BILL_OF_LADING",
        {
            "vessel_name": "MV Meridian Halo",
            "port_of_loading": "Port Lumen",
            "port_of_discharge": "Port Azure",
        },
        document=doc,
    )
    return case


def test_supported_risk_signals_persist_with_policy_and_source_audit(database):
    with Session(database) as s:
        case = risk_case(s)
        run = run_risk_checks(s, Settings(_env_file=None), case.case_id)
        assert run.status == "COMPLETED"
        assert sorted(f.category for f in run.findings) == ["port", "screening", "vessel"]
        for f in run.findings:
            assert f.evidence_json["provider"]["name"].startswith("SYNTHETIC_")
            assert f.evidence_json["rule"]["version"] == f.rule_version == 1
            if f.category in {"port", "vessel"}:
                e = f.evidence_json["subject"]["evidence"][0]
                assert e["source_verified"] and e["fact_id"] and e["source_text"]
        assert any(c.status == "NOT_CHECKED" for c in run.checks)
        assert not any("decision" in f.finding_type.lower() for f in run.findings)


def test_clean_case_optional_absence_no_false_material_findings(database):
    with Session(database) as s:
        case = import_case(s)
        run = run_risk_checks(s, Settings(_env_file=None), case.case_id)
        assert run.status == "COMPLETED" and not run.findings
        assert any(c.status == "NOT_APPLICABLE" for c in run.checks)
        assert any(
            e.rule_id == "RISK-DUP-FINANCE-001" and e.status == "NOT_CHECKED"
            for e in run.executions
        )


def test_provider_failure_is_partial_and_never_persists_private_error(database):
    class BadProvider(SyntheticScreeningProvider):
        def check(self, subject):
            return {
                "status": "CLEAR",
                "reason": "test",
                "details": {"authorization": "private-value"},
            }

    with Session(database) as s:
        case = risk_case(s)
        registry = ProviderRegistry([BadProvider(load_references())])
        run = run_risk_checks(s, Settings(_env_file=None), case.case_id, registry=registry)
        assert run.status == "PARTIAL"
        assert any(c.status == "PROVIDER_ERROR" for c in run.checks)
        assert "private-value" not in str([c.result_json for c in run.checks])


def test_rerun_snapshot_and_submission_dedup_are_immutable(database):
    with Session(database) as s:
        case = risk_case(s)
        settings = Settings(_env_file=None)
        key = str(uuid4())
        first = run_risk_checks(s, settings, case.case_id, key)
        original = copy.deepcopy(first.input_snapshot_json)
        checks = copy.deepcopy([c.result_json for c in first.checks])
        assert risk_inputs_current(s, settings, first)
        assert run_risk_checks(s, settings, case.case_id, key).id == first.id
        party = s.scalar(select(CaseParty))
        party.party_name = "Other party"
        s.commit()
        assert not risk_inputs_current(s, settings, first)
        second = run_risk_checks(s, settings, case.case_id)
        assert second.id != first.id and second.run_number == first.run_number + 1
        old = get_risk_run(s, first.id)
        assert old.input_snapshot_json == original and [c.result_json for c in old.checks] == checks
        assert s.scalar(select(RiskRun).where(RiskRun.id == first.id)).status == "COMPLETED"
