from collections import Counter

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.session import get_session
from app.main import app
from app.models.domain import Base
from app.services.demo_import import ingest, prepare, read_sources
from tests.test_import import RAW


@pytest.fixture()
def source():
    return read_sources(RAW)


@pytest.fixture()
def client(source):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        ingest(session, source)

    def override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    engine.dispose()


def test_listing_and_filters(client, source):
    response = client.get("/api/v1/cases")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == len(source["trade_cases"])
    assert {item["case_id"] for item in payload["items"]} == {
        r["case_id"] for r in source["trade_cases"]
    }
    assert all(item["is_synthetic"] for item in payload["items"])
    known = source["trade_cases"][0]
    assert client.get("/api/v1/cases", params={"q": known["case_id"]}).json()["total"] == 1
    assert len(client.get("/api/v1/cases", params={"limit": 1, "offset": 1}).json()["items"]) == 1
    assert client.get("/api/v1/cases", params={"limit": 0}).status_code == 422


def test_known_case_and_related_inventory(client, source):
    case_id = source["trade_cases"][0]["case_id"]
    payload = client.get(f"/api/v1/cases/{case_id}").json()
    assert payload["applicant"] == source["trade_cases"][0]["applicant"]
    assert payload["priority"] is None
    prepared = prepare(source)
    for source_name, key, route in [
        ("case_parties", "parties", "parties"),
        ("case_documents", "documents", "documents"),
        ("trade_lines", "trade_lines", "trade-lines"),
        ("discrepancies", "discrepancies", "discrepancies"),
        ("risk_events", "risk_events", "risk-events"),
        ("approval_events", "approvals", "approvals"),
    ]:
        rows = [r for r in prepared[source_name] if r["case_id"] == case_id]
        assert len(payload[key]) == len(rows)
        assert client.get(f"/api/v1/cases/{case_id}/{route}").json() == payload[key]
    assert "source_key" not in str(payload) and "dataset_key" not in str(payload)


def test_unknown_case(client):
    assert client.get("/api/v1/cases/does-not-exist").status_code == 404
    assert client.get("/api/v1/cases/does-not-exist/documents").status_code == 404


def test_summary_matches_actual_source(client, source):
    summary = client.get("/api/v1/dashboard/summary").json()
    assert summary["total_cases"] == len(source["trade_cases"])
    assert summary["synthetic_cases"] == len(source["trade_cases"])
    expected = Counter(row["expected_decision"] for row in source["trade_cases"])
    for key in ("PASS", "REFER", "BLOCK"):
        assert summary["expected_outcomes"][key] == expected[key]
    assert sum(row["count"] for row in summary["product_distribution"]) == len(
        source["trade_cases"]
    )
