from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_returns_ready() -> None:
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "ok",
    }


def test_root_returns_ok() -> None:
    response = client.get("/api/v1/")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_openapi_spec_is_valid() -> None:
    response = client.get("/api/openapi.json")

    assert response.status_code == 200
    body = response.json()
    assert body["openapi"].startswith("3.")
    assert body["info"]["title"]
