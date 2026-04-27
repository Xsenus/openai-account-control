"""Coverage for account auth onboarding routes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.auth_job_service import AuthJob


def login(client: TestClient) -> None:
    """Authenticate a test client as the bootstrap operator."""
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "ChangeMe123!"},
    )
    assert response.status_code == 200


def create_account(client: TestClient) -> str:
    """Create a simple account entry and return its id."""
    response = client.post(
        "/api/accounts",
        json={
            "label": "Demo account",
            "email_hint": "demo@example.com",
            "notes": "",
            "is_enabled": True,
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_browser_login_route_returns_serialized_job(monkeypatch) -> None:
    """The local-login route should return job metadata instead of crashing on dataclass slots."""
    fake_job = AuthJob(
        job_id="job-1",
        account_id="account-1",
        status="queued",
        message="Browser opened.",
        started_at=datetime.now(timezone.utc),
        finished_at=None,
    )

    async def fake_start(**_kwargs) -> AuthJob:
        return fake_job

    with TestClient(app) as client:
        login(client)
        account_id = create_account(client)
        fake_job.account_id = account_id
        monkeypatch.setattr(app.state.auth_job_service, "start", fake_start)

        response = client.post(
            f"/api/accounts/{account_id}/auth/browser-login",
            json={"timeout_seconds": 120, "headless": False},
        )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-1"
    assert response.json()["account_id"] == account_id
    assert response.json()["status"] == "queued"


def test_import_rejects_openai_session_export_json() -> None:
    """Users should get a clear 400 when they paste token/session metadata instead of storage_state."""
    with TestClient(app) as client:
        login(client)
        account_id = create_account(client)

        response = client.post(
            f"/api/accounts/{account_id}/auth/import",
            json={
                "storage_state": {
                    "user": {"email": "demo@example.com"},
                    "accessToken": "token",
                    "sessionToken": "session",
                }
            },
        )

    assert response.status_code == 400
    assert "Playwright storage_state" in response.json()["detail"]
    assert "cookies" in response.json()["detail"]
