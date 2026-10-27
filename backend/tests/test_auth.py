from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def registered_user(
    auth_client: TestClient,
) -> Generator[dict[str, str], None, None]:
    response = auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "Test.User@example.com",
            "password": "correct-horse-battery-staple",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 201
    yield response.json()


def test_register_normalizes_email_and_returns_customer(
    auth_client: TestClient,
) -> None:
    response = auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "Test.User@example.com",
            "password": "correct-horse-battery-staple",
            "full_name": "Test User",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "test.user@example.com"
    assert body["full_name"] == "Test User"
    assert body["role"] == "customer"
    assert "password" not in body
    assert "password_hash" not in body


def test_register_rejects_duplicate_email_case_insensitively(
    auth_client: TestClient,
    registered_user: dict[str, str],
) -> None:
    response = auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": registered_user["email"].upper(),
            "password": "another-correct-password",
            "full_name": "Duplicate User",
        },
    )

    assert response.status_code == 409


def test_login_and_access_current_user(
    auth_client: TestClient,
    registered_user: dict[str, str],
) -> None:
    response = auth_client.post(
        "/api/v1/auth/login",
        json={
            "email": registered_user["email"],
            "password": "correct-horse-battery-staple",
        },
    )

    assert response.status_code == 200
    token = response.json()["access_token"]
    assert token
    assert "refresh_token" not in response.json()
    assert response.json()["token_type"] == "bearer"
    assert auth_client.cookies.get("takeaway_access")
    assert auth_client.cookies.get("takeaway_refresh")
    assert auth_client.cookies.get("takeaway_csrf")

    me_response = auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["id"] == registered_user["id"]
    assert me_response.json()["email"] == registered_user["email"]
    assert me_response.json()["role"] == "customer"


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("test.user@example.com", "wrong-password"),
        ("unknown@example.com", "correct-horse-battery-staple"),
    ],
)
def test_login_rejects_invalid_credentials(
    auth_client: TestClient,
    registered_user: dict[str, str],
    email: str,
    password: str,
) -> None:
    response = auth_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_current_user_requires_token(auth_client: TestClient) -> None:
    response = auth_client.get("/api/v1/auth/me")

    assert response.status_code == 401


def _csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.cookies.get("takeaway_csrf")
    assert token
    return {"X-CSRF-Token": token}


def test_session_cookie_authenticates_without_bearer(
    auth_client: TestClient,
    registered_user: dict[str, str],
) -> None:
    login = auth_client.post(
        "/api/v1/auth/login",
        json={
            "email": registered_user["email"],
            "password": "correct-horse-battery-staple",
        },
    )
    assert login.status_code == 200

    me_response = auth_client.get("/api/v1/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["id"] == registered_user["id"]


def test_refresh_rotates_and_rejects_reuse(
    auth_client: TestClient,
    registered_user: dict[str, str],
) -> None:
    auth_client.post(
        "/api/v1/auth/login",
        json={
            "email": registered_user["email"],
            "password": "correct-horse-battery-staple",
        },
    )
    first_refresh = auth_client.cookies.get("takeaway_refresh")
    assert first_refresh

    rotated = auth_client.post(
        "/api/v1/auth/refresh",
        headers=_csrf_headers(auth_client),
    )
    assert rotated.status_code == 200
    assert "refresh_token" not in rotated.json()
    second_refresh = auth_client.cookies.get("takeaway_refresh")
    assert second_refresh
    assert second_refresh != first_refresh

    auth_client.cookies.set("takeaway_refresh", first_refresh, path="/api/v1/auth")
    reuse = auth_client.post(
        "/api/v1/auth/refresh",
        headers=_csrf_headers(auth_client),
    )
    assert reuse.status_code == 401

    auth_client.cookies.set("takeaway_refresh", second_refresh, path="/api/v1/auth")
    after_reuse = auth_client.post(
        "/api/v1/auth/refresh",
        headers=_csrf_headers(auth_client),
    )
    assert after_reuse.status_code == 401


def test_logout_revokes_refresh_token(
    auth_client: TestClient,
    registered_user: dict[str, str],
) -> None:
    auth_client.post(
        "/api/v1/auth/login",
        json={
            "email": registered_user["email"],
            "password": "correct-horse-battery-staple",
        },
    )
    refresh_token = auth_client.cookies.get("takeaway_refresh")
    csrf = auth_client.cookies.get("takeaway_csrf")
    assert refresh_token
    assert csrf

    logout = auth_client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": csrf},
    )
    assert logout.status_code == 204

    auth_client.cookies.set("takeaway_refresh", refresh_token, path="/api/v1/auth")
    auth_client.cookies.set("takeaway_csrf", csrf)
    refresh = auth_client.post(
        "/api/v1/auth/refresh",
        headers={"X-CSRF-Token": csrf},
    )
    assert refresh.status_code == 401


def test_register_rejects_short_password(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "short.password@example.com",
            "password": "short",
            "full_name": "Test User",
        },
    )

    assert response.status_code == 422
