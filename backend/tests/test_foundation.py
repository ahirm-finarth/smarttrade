from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.exc import OperationalError

from app.core.config import Settings
from app.main import app


def test_health(monkeypatch):
    monkeypatch.setattr("app.main.database_connected", lambda: True)
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["database"] == "connected"
    assert "key" not in response.text.lower()


def test_database_failure_health(monkeypatch):
    monkeypatch.setattr("app.main.database_connected", lambda: False)
    response = TestClient(app).get("/health")
    assert response.status_code == 503
    assert response.json()["database"] == "unavailable"


def test_secure_configuration():
    settings = Settings(
        _env_file=None,
        DATABASE_URL="mysql://test:placeholder@localhost/demo",
        llm_api_key=SecretStr("placeholder"),
    )
    assert settings.sqlalchemy_url.drivername == "mysql+pymysql"
    assert settings.sqlalchemy_url.query["charset"] == "utf8mb4"
    assert "placeholder" not in repr(settings)


def test_db_aliases():
    settings = Settings(
        _env_file=None,
        DB_HOST="localhost",
        DB_USER="test",
        DB_PASSWORD="placeholder",
        DB_NAME="demo",
    )
    assert settings.sqlalchemy_url.database == "demo"


def test_connection_abstraction(monkeypatch):
    from app.db.session import database_connected

    def fail():
        raise OperationalError("SELECT 1", {}, Exception("private"))

    monkeypatch.setattr("app.db.session.get_engine", fail)
    assert database_connected() is False
