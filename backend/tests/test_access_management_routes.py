"""Coverage for operator management in the settings API."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app


def login(client: TestClient, username: str = "admin", password: str = "ChangeMe123!") -> None:
    """Authenticate a test client as the bootstrap operator."""
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200


def test_operator_management_and_password_change() -> None:
    """Operators should be creatable from the UI and able to change their own password."""
    with TestClient(app) as client:
        login(client)

        create_response = client.post(
            "/api/settings/access/users",
            json={
                "username": "ops2",
                "password": "NewStrongPass123!",
                "is_active": True,
            },
        )
        assert create_response.status_code == 200
        created_user = create_response.json()
        assert created_user["username"] == "ops2"
        assert created_user["is_active"] is True

        list_response = client.get("/api/settings/access/users")
        assert list_response.status_code == 200
        assert [user["username"] for user in list_response.json()] == ["admin", "ops2"]

        password_response = client.post(
            "/api/settings/access/change-password",
            json={
                "current_password": "ChangeMe123!",
                "new_password": "ChangedAgain123!",
            },
        )
        assert password_response.status_code == 200

        logout_response = client.post("/api/auth/logout")
        assert logout_response.status_code == 200

        old_login_response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "ChangeMe123!"},
        )
        assert old_login_response.status_code == 401

        new_login_response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "ChangedAgain123!"},
        )
        assert new_login_response.status_code == 200


def test_last_active_operator_cannot_be_disabled() -> None:
    """Guardrails should prevent locking the panel by disabling the only active operator."""
    with TestClient(app) as client:
        login(client)

        list_response = client.get("/api/settings/access/users")
        user_id = list_response.json()[0]["id"]

        disable_response = client.put(
            f"/api/settings/access/users/{user_id}",
            json={"is_active": False},
        )
        assert disable_response.status_code == 400
        assert disable_response.json()["detail"] == "At least one active operator must remain."
