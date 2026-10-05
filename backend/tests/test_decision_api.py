from contextlib import contextmanager
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.v1 import decisions
from app.db.session import get_session
from app.integrations.llm.client import LLMUnavailable
from app.main import app
from tests.test_decision_engine import prepared_case
from tests.test_examination_engine import database as database_fixture  # noqa: F401


@contextmanager
def api_client(database, risk=False):
    with Session(database) as s:
        case_id = prepared_case(s, risk=risk).case_id

    def session():
        with Session(database) as s:
            yield s

    app.dependency_overrides[get_session] = session
    try:
        with TestClient(app) as client:
            yield client, case_id
    finally:
        app.dependency_overrides.clear()


def test_decision_api_routes_run_versions_tasks_workflow_and_audit(database):
    with api_client(database) as (client, case_id):
        prefix = f"/api/v1/cases/{case_id}"
        assert client.get(prefix + "/workflow").json()["state"] == "READY_FOR_DECISION"
        assert client.get(prefix + "/decisions/latest").status_code == 404
        key = str(uuid4())
        response = client.post(prefix + "/decisions", json={"request_id": key})
        assert response.status_code == 200
        detail = response.json()
        id = detail["run"]["id"]
        assert detail["run"]["recommended_decision"] == "PASS"
        assert detail["effective_final_outcome"] is None and detail["demo_only"]
        assert (
            client.post(prefix + "/decisions", json={"request_id": key}).json()["run"]["id"] == id
        )
        assert len(client.get(prefix + "/decisions").json()) == 1
        assert client.get(prefix + "/decisions/latest").json()["run"]["id"] == id
        assert client.get(f"/api/v1/decisions/{id}/reasons").status_code == 200
        task_id = detail["tasks"][0]["id"]
        assert client.get(f"/api/v1/tasks/{task_id}").status_code == 200
        assert len(client.get(prefix + "/tasks").json()) == 1
        assert client.get("/api/v1/demo-actors").json()[0]["actor_id"] == "maker.demo"
        made = client.post(
            f"/api/v1/tasks/{task_id}/actions",
            json={
                "action": "SUBMIT_FOR_CHECKER",
                "actor_id": "dual.demo",
                "comment": "Reviewed the synthetic sources",
                "expected_revision": 1,
            },
        ).json()
        checker = next(t for t in made["tasks"] if t["task_type"] == "CHECKER_APPROVAL")
        payload = {
            "action": "APPROVE",
            "actor_id": "dual.demo",
            "comment": "Self-check attempt",
            "expected_revision": made["workflow"]["revision"],
        }
        denied = client.post(f"/api/v1/tasks/{checker['id']}/actions", json=payload)
        assert denied.status_code == 403 and "Segregation" in denied.json()["detail"]
        payload["actor_id"] = "checker.demo"
        approved = client.post(f"/api/v1/tasks/{checker['id']}/actions", json=payload)
        assert approved.status_code == 200 and approved.json()["effective_final_outcome"] == "PASS"
        assert client.get(prefix + "/workflow").json()["effective_final_outcome"] == "PASS"
        audit = client.get(prefix + "/audit").json()
        assert {e["event_type"] for e in audit} >= {
            "DOCUMENT_PROCESSING",
            "DOCUMENTARY_EXAMINATION",
            "RISK_RUN",
            "DECISION_RUN",
            "TASK_CREATED",
            "MAKER_SUBMITTED",
            "FINAL_PASS",
        }
        assert [e["timestamp"] for e in audit] == sorted(
            [e["timestamp"] for e in audit], reverse=True
        )
        assert "storage_path" not in str(detail) and "expected_decision" not in str(detail)


def test_decision_api_rejects_stale_authority_bad_payloads_and_unknowns(database):
    with api_client(database) as (client, case_id):
        prefix = f"/api/v1/cases/{case_id}"
        detail = client.post(prefix + "/decisions").json()
        task = detail["tasks"][0]
        assert (
            client.post(prefix + "/decisions", json={"recommended_decision": "PASS"}).status_code
            == 422
        )
        assert (
            client.post(
                f"/api/v1/tasks/{task['id']}/actions",
                json={
                    "action": "APPROVE",
                    "actor_id": "checker.demo",
                    "comment": " ",
                    "expected_revision": 1,
                },
            ).status_code
            == 422
        )
        assert client.get("/api/v1/decisions/999999").status_code == 404
        assert client.get("/api/v1/tasks/999999").status_code == 404
        assert client.get("/api/v1/cases/unknown/decisions").status_code == 404
        assert client.get("/api/v1/cases/unknown/audit").status_code == 404
        client.post(prefix + "/risk-runs")
        old = client.get(f"/api/v1/decisions/{detail['run']['id']}").json()
        assert not old["inputs_current"] and old["effective_final_outcome"] is None
        assert (
            client.post(
                f"/api/v1/tasks/{task['id']}/actions",
                json={
                    "action": "SUBMIT_FOR_CHECKER",
                    "actor_id": "maker.demo",
                    "comment": "Attempt stale submission",
                    "expected_revision": 1,
                },
            ).status_code
            == 409
        )


def test_refer_override_api_and_optional_advisory_failure_leave_authority_intact(
    database, monkeypatch
):
    with api_client(database, risk=True) as (client, case_id):
        detail = client.post(f"/api/v1/cases/{case_id}/decisions").json()
        id = detail["run"]["id"]
        reason = next(r for r in detail["reasons"] if r["impact"] == "REFER")
        payload = {
            "actor_id": "maker.demo",
            "reason_code": "ACCEPT_REVIEWED_EXCEPTION",
            "reason_ids": [reason["id"]],
            "rationale": "Unauthorized request",
            "expected_revision": 1,
        }
        assert client.post(f"/api/v1/decisions/{id}/override", json=payload).status_code == 403

        def unavailable(*args, **kwargs):
            raise LLMUnavailable("private-provider-data")

        monkeypatch.setattr(decisions, "draft_exception_advice", unavailable)
        response = client.post(
            f"/api/v1/decisions/{id}/exception-summary", json={"actor_id": "maker.demo"}
        )
        assert response.status_code == 503 and "private-provider-data" not in response.text
        unchanged = client.get(f"/api/v1/decisions/{id}").json()
        assert unchanged["run"]["recommended_decision"] == "REFER"
        assert unchanged["workflow"]["final_outcome"] is None and not unchanged["overrides"]
