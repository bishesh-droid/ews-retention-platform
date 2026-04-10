from backend.routes import monitoring
from backend.main import health_check
from backend.api.deps import get_current_user
from pathlib import Path
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure local imports work when pytest is run from repo root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class _TestUser:
    id = 1
    role = "admin"
    is_superuser = True
    is_active = True


@pytest.fixture
def monitoring_app() -> FastAPI:
    app = FastAPI()
    app.include_router(monitoring.router, prefix="/api/v1")
    return app


@pytest.fixture
def authed_client(monitoring_app: FastAPI) -> TestClient:
    monitoring_app.dependency_overrides[get_current_user] = lambda: _TestUser()
    return TestClient(monitoring_app)


@pytest.fixture
def unauthed_client(monitoring_app: FastAPI) -> TestClient:
    return TestClient(monitoring_app)


def test_health_check_returns_success_envelope():
    payload = health_check()

    assert payload["success"] is True
    assert payload["message"] == "OK"
    assert payload["data"]["status"] == "healthy"
    assert isinstance(payload["data"]["timestamp"], float)
    assert "meta" in payload


def test_get_prediction_stats_unit_success(monkeypatch):
    expected = {"total_predictions": 12, "model_used": False}
    monkeypatch.setattr(monitoring.ml_service, "get_runtime_stats", lambda: expected)

    response = monitoring.get_prediction_stats(_user=_TestUser())

    assert response["success"] is True
    assert response["message"] == "ML pipeline stats"
    assert response["data"] == expected


def test_monitoring_endpoint_requires_auth(unauthed_client: TestClient):
    response = unauthed_client.get("/api/v1/monitoring/predictions")
    assert response.status_code == 401


def test_monitoring_endpoint_returns_stats(authed_client: TestClient, monkeypatch):
    expected = {
        "total_predictions": 5,
        "model_used": False,
        "model_status": "rule-based",
    }
    monkeypatch.setattr(monitoring.ml_service, "get_runtime_stats", lambda: expected)

    response = authed_client.get("/api/v1/monitoring/predictions")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "ML pipeline stats"
    assert body["data"] == expected


def test_monitoring_endpoint_handles_stats_failure(authed_client: TestClient, monkeypatch):
    def _raise_runtime_error():
        raise RuntimeError("stats backend unavailable")

    monkeypatch.setattr(monitoring.ml_service, "get_runtime_stats", _raise_runtime_error)

    response = authed_client.get("/api/v1/monitoring/predictions")

    assert response.status_code == 503
    assert response.json()["detail"] == "Monitoring service temporarily unavailable."
