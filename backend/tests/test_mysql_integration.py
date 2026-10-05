"""Opt-in checks against supplied MySQL. Never create/drop/truncate any schema."""

import os
from collections import Counter

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.main import app
from app.models.domain import TradeCase
from app.services.demo_import import DATASET_KEY, SPECS, ingest, prepare, read_sources
from tests.test_import import RAW

pytestmark = pytest.mark.skipif(
    os.environ.get("SMART_TRADE_MYSQL_TESTS") != "1", reason="Opt-in supplied MySQL validation"
)


def test_mysql_schema_and_exact_source_records():
    engine = get_engine()
    inspector = inspect(engine)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1
        assert connection.execute(
            text("SELECT version_num FROM smart_trade_alembic_version")
        ).scalar_one()
        collations = connection.execute(
            text(
                "SELECT TABLE_NAME, TABLE_COLLATION FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME LIKE 'smart_trade_%'"
            )
        ).all()
        assert all(collation.startswith("utf8mb4") for _, collation in collations)
    source = prepare(read_sources(RAW))
    with Session(engine) as session:
        cases = {
            case.case_id: case
            for case in session.scalars(
                select(TradeCase).where(TradeCase.dataset_key == DATASET_KEY)
            )
        }
        assert len(cases) == len(source["trade_cases"])
        for name, (model, _, _) in SPECS.items():
            assert model.__tablename__ in inspector.get_table_names()
            if name not in {"trade_cases", "risk_rules", "reference_screening"}:
                assert inspector.get_foreign_keys(model.__tablename__)
                statement = (
                    select(func.count())
                    .select_from(model)
                    .join(TradeCase)
                    .where(
                        TradeCase.dataset_key == DATASET_KEY, model.source_key.startswith("demo:")
                    )
                )
            else:
                statement = (
                    select(func.count()).select_from(model).where(model.dataset_key == DATASET_KEY)
                )
            assert session.scalar(statement) == len(source[name])
        for row in source["trade_cases"]:
            record = cases[row["case_id"]]
            for key, value in row.items():
                assert getattr(record, key) == value
            assert record.created_at.tzinfo is not None


def test_mysql_seed_idempotency_preserves_ids_and_record_timestamps():
    engine = get_engine()
    source = read_sources(RAW)

    def snapshot():
        with Session(engine) as session:
            return {
                name: [
                    tuple(row)
                    for row in session.execute(select(model.__table__).order_by(model.id))
                ]
                for name, (model, _, _) in SPECS.items()
            }

    before = snapshot()
    for _ in range(2):
        with Session(engine) as session, session.begin():
            counts = ingest(session, source)
            assert counts == {name: len(rows) for name, rows in source.items()}
    assert snapshot() == before


def test_mysql_api_seeded_workflows():
    source = read_sources(RAW)
    with TestClient(app) as client:
        assert client.get("/health").json()["database"] == "connected"
        payload = client.get("/api/v1/cases").json()
        assert {row["case_id"] for row in source["trade_cases"]}.issubset(
            {row["case_id"] for row in payload["items"]}
        )
        for row in source["trade_cases"]:
            response = client.get("/api/v1/cases/" + row["case_id"])
            assert response.status_code == 200
            assert response.json()["expected_decision"] == row["expected_decision"]
        assert client.get("/api/v1/cases/unknown-integration-case").status_code == 404
        summary = client.get("/api/v1/dashboard/summary").json()
        assert summary["synthetic_cases"] == len(source["trade_cases"])
        expected = Counter(row["expected_decision"] for row in source["trade_cases"])
        for outcome, count in expected.items():
            assert summary["expected_outcomes"][outcome] >= count


def test_mysql_examination_schema_and_persisted_evidence_routes():
    from app.models.examination import ExaminationRun
    from app.rules import load_rules

    engine = get_engine()
    inspector = inspect(engine)
    for name in (
        "smart_trade_examination_runs",
        "smart_trade_rule_executions",
        "smart_trade_fact_relations",
        "smart_trade_detected_discrepancies",
    ):
        assert name in inspector.get_table_names()
        assert inspector.get_foreign_keys(name)
        assert inspector.get_indexes(name)
    with Session(engine) as session, TestClient(app) as client:
        cases = session.scalars(select(TradeCase).where(TradeCase.dataset_key == DATASET_KEY)).all()
        for case in cases:
            run = session.scalar(
                select(ExaminationRun)
                .where(ExaminationRun.case_pk == case.id)
                .order_by(ExaminationRun.run_number.desc())
                .limit(1)
            )
            assert run is not None
            response = client.get(f"/api/v1/examinations/{run.id}")
            assert response.status_code == 200
            detail = response.json()
            assert len(detail["executions"]) == len(load_rules(case.product_playbook))
            for finding in detail["findings"]:
                for side in ("expected_json", "observed_json"):
                    evidence = finding[side]
                    assert evidence["fact_id"] and evidence["source_verified"]
                    assert evidence["source_text"] and evidence["page_number"] >= 1
            for relation in detail["relations"]:
                assert relation["expected"]["fact_id"] == relation["source_fact_pk"]
                assert relation["observed"]["fact_id"] == relation["target_fact_pk"]


def test_mysql_risk_schema_and_persisted_provider_evidence_routes():
    from app.models.risk import RiskRun

    engine = get_engine()
    inspector = inspect(engine)
    for name in (
        "smart_trade_risk_runs",
        "smart_trade_provider_checks",
        "smart_trade_risk_rule_executions",
        "smart_trade_detected_risk_findings",
    ):
        assert name in inspector.get_table_names()
        assert inspector.get_foreign_keys(name) and inspector.get_indexes(name)
    with Session(engine) as session, TestClient(app) as client:
        cases = session.scalars(select(TradeCase).where(TradeCase.dataset_key == DATASET_KEY)).all()
        for case in cases:
            run = session.scalar(
                select(RiskRun)
                .where(RiskRun.case_pk == case.id)
                .order_by(RiskRun.run_number.desc())
                .limit(1)
            )
            assert run is not None
            response = client.get(f"/api/v1/risk-runs/{run.id}")
            assert response.status_code == 200
            detail = response.json()
            assert detail["run"]["case_id"] == case.case_id
            assert detail["run"]["summary_json"]["decision_computed"] is False
            assert len(detail["checks"]) == sum(run.summary_json["checks"].values())
            assert len(detail["executions"]) == run.summary_json["rules_executed"]
            for finding in detail["findings"]:
                evidence = finding["evidence_json"]
                assert evidence["provider"]["result"]["synthetic"] is True
                assert evidence["rule"]["version"] == finding["rule_version"]
                assert evidence["provider"]["result"]["matched_records"]
                if finding["category"] in {"port", "vessel"}:
                    assert evidence["subject"]["evidence"][0]["source_verified"]
            assert (
                client.get(f"/api/v1/cases/{case.case_id}/duplicate-candidates").json()[
                    "financing_status"
                ]
                == "NOT_CHECKED"
            )
