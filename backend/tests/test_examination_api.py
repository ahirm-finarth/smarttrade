from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.main import app
from app.models.domain import TradeCase
from tests.test_examination_engine import database as database_fixture  # noqa: F401
from tests.test_examination_engine import import_case


def test_examination_api_history_provenance_and_ownership(database):
    with Session(database) as s:
        case = import_case(s, amount="USD 106.00")
        s.add(TradeCase(case_id="OTHER", product_playbook="Import LC"))
        s.commit()
        case_id = case.case_id

    def session():
        with Session(database) as s:
            yield s

    app.dependency_overrides[get_session] = session
    try:
        with TestClient(app) as client:
            base = f"/api/v1/cases/{case_id}"
            assert client.get(base + "/examinations").json() == []
            assert client.get(base + "/examinations/latest").status_code == 404
            assert client.get(base + "/extracted-facts").json()["facts"]
            assert client.get(base + "/evidence-relations").json() == []
            key = {"request_id": str(uuid4())}
            response = client.post(base + "/examinations", json=key)
            assert response.status_code == 200
            data = response.json()
            run_id = data["run"]["id"]
            assert data["run"]["status"] == "DISCREPANCIES_FOUND" and data["inputs_current"]
            assert data["findings"][0]["expected_json"]["source_text"]
            assert data["findings"][0]["observed_json"]["source_text"]
            assert client.post(base + "/examinations", json=key).json()["run"]["id"] == run_id
            assert len(client.get(base + "/examinations").json()) == 1
            assert client.get(base + "/examinations/latest").json()["run"]["id"] == run_id
            assert client.get(f"/api/v1/examinations/{run_id}").status_code == 200
            assert client.get(f"/api/v1/examinations/{run_id}/rule-executions").json()
            assert client.get(f"/api/v1/examinations/{run_id}/findings").json()
            relations = client.get(base + "/evidence-relations").json()
            assert relations[0]["expected"]["document_version_id"]
            assert (
                client.get(f"/api/v1/cases/OTHER/evidence-relations?run_id={run_id}").status_code
                == 404
            )
            assert client.get("/api/v1/examinations/999999").status_code == 404
            assert client.post("/api/v1/cases/MISSING/examinations").status_code == 404
            assert (
                client.post(base + "/examinations", json={"request_id": "invalid"}).status_code
                == 422
            )
            assert "storage_path" not in response.text and "expected_decision" not in response.text
    finally:
        app.dependency_overrides.clear()


def test_unsupported_playbook_is_not_reported_as_clean(database):
    with Session(database) as s:
        s.add(TradeCase(case_id="UNCONFIGURED", product_playbook="Other"))
        s.commit()

    def session():
        with Session(database) as s:
            yield s

    app.dependency_overrides[get_session] = session
    try:
        with TestClient(app) as client:
            assert client.post("/api/v1/cases/UNCONFIGURED/examinations").status_code == 422
    finally:
        app.dependency_overrides.clear()
