from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.main import app
from tests.test_examination_engine import database as database_fixture  # noqa: F401
from tests.test_risk_orchestration import risk_case


def test_risk_routes_history_audit_duplicate_candidates_and_errors(database):
    with Session(database) as s:
        case_id = risk_case(s).case_id

    def session():
        with Session(database) as s:
            yield s

    app.dependency_overrides[get_session] = session
    try:
        with TestClient(app) as client:
            prefix = f"/api/v1/cases/{case_id}/risk-runs"
            assert client.get(prefix + "/latest").status_code == 404
            key = str(uuid4())
            response = client.post(prefix, json={"request_id": key})
            assert response.status_code == 200
            detail = response.json()
            id = detail["run"]["id"]
            assert detail["inputs_current"] and detail["synthetic"]
            assert len(detail["findings"]) == 3
            assert client.post(prefix, json={"request_id": key}).json()["run"]["id"] == id
            assert len(client.get(prefix).json()) == 1
            assert client.get(prefix + "/latest").json()["run"]["id"] == id
            for path in ("", "/provider-checks", "/rule-executions", "/findings"):
                assert client.get(f"/api/v1/risk-runs/{id}" + path).status_code == 200
            assert client.get(f"/api/v1/cases/{case_id}/duplicate-candidates").status_code == 200
            assert client.post(prefix, json={"request_id": "invalid"}).status_code == 422
            assert client.post(prefix, json={"expected_decision": "BLOCK"}).status_code == 422
            assert client.get("/api/v1/risk-runs/99999").status_code == 404
            assert client.get("/api/v1/cases/unknown/risk-runs").status_code == 404
            assert "storage_path" not in str(detail)
    finally:
        app.dependency_overrides.clear()
