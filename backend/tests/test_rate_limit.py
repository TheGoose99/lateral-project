from fastapi.testclient import TestClient
from starlette.requests import Request

from app.core.config import get_settings
from app.core.rate_limit import client_ip, limiter


def _request(headers: list[tuple[bytes, bytes]], client: tuple[str, int] | None) -> Request:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": headers,
        "client": client,
        "server": ("testserver", 80),
    }
    return Request(scope)


def test_client_ip_uses_first_forwarded_for_hop() -> None:
    # Nginx sets X-Forwarded-For to $remote_addr, so the first hop is the
    # connecting client. A spoofed extra hop must not replace that value.
    request = _request(
        [(b"x-forwarded-for", b"203.0.113.9, 198.51.100.2")],
        ("127.0.0.1", 12345),
    )
    assert client_ip(request) == "203.0.113.9"


def test_client_ip_falls_back_to_socket_peer() -> None:
    request = _request([], ("10.0.0.8", 44321))
    assert client_ip(request) == "10.0.0.8"


def test_login_is_rate_limited(auth_client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("AUTH_RATE_LIMIT_PER_MINUTE", "2")
    get_settings.cache_clear()
    limiter._hits.clear()

    try:
        payload = {
            "email": "unknown@example.com",
            "password": "definitely-wrong-password",
        }
        first = auth_client.post("/api/v1/auth/login", json=payload)
        second = auth_client.post("/api/v1/auth/login", json=payload)
        third = auth_client.post("/api/v1/auth/login", json=payload)

        assert first.status_code == 401
        assert second.status_code == 401
        assert third.status_code == 429
        assert third.json()["detail"] == "Too many requests. Please try again shortly."
    finally:
        get_settings.cache_clear()
        limiter._hits.clear()


def test_cors_allows_configured_frontend_origin(auth_client: TestClient) -> None:
    response = auth_client.options(
        "/api/v1/restaurants",
        headers={
            "Origin": "http://localhost:8080",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code in {200, 204}
    assert response.headers.get("access-control-allow-origin") == "http://localhost:8080"
