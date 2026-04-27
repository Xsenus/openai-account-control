"""Route-level coverage for panel authentication."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app


def test_public_session_endpoint_reports_logged_out_state() -> None:
    """Browsers should learn that login is required before any protected call."""
    with TestClient(app) as client:
        response = client.get("/api/auth/session")

    assert response.status_code == 200
    assert response.json()["auth_enabled"] is True
    assert response.json()["authenticated"] is False


def test_protected_api_requires_login() -> None:
    """Settings should stay hidden until the panel admin logs in."""
    with TestClient(app) as client:
        response = client.get("/api/settings")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required."


def test_login_unlocks_and_logout_locks_again() -> None:
    """A valid login cookie should unlock protected routes until logout."""
    with TestClient(app) as client:
        login_response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "ChangeMe123!"},
        )
        assert login_response.status_code == 200
        assert login_response.json()["authenticated"] is True
        assert "control_center_session" in login_response.headers.get("set-cookie", "")

        protected_response = client.get("/api/settings")
        assert protected_response.status_code == 200

        logout_response = client.post("/api/auth/logout")
        assert logout_response.status_code == 200
        assert logout_response.json()["authenticated"] is False

        denied_response = client.get("/api/settings")
        assert denied_response.status_code == 401
