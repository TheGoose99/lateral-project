from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, require_role
from app.models.user import User


@pytest.fixture()
def authorization_client():
    app = FastAPI()

    @app.get("/staff")
    def staff_endpoint(
        user: User = Depends(require_role("staff", "admin")),
    ):
        return {"role": user.role}

    return app


@pytest.mark.parametrize(
    ("role", "expected_status"),
    [
        ("customer", 403),
        ("staff", 200),
        ("admin", 200),
    ],
)
def test_staff_endpoint_role_access(authorization_client, role, expected_status):
    user = User(
        id=uuid4(),
        email=f"{role}@example.com",
        password_hash="not-used",
        full_name="Test User",
        role=role,
        is_active=True,
    )

    authorization_client.dependency_overrides = {
        get_current_user: lambda: user,
    }

    with TestClient(authorization_client) as client:
        response = client.get("/staff")

    assert response.status_code == expected_status

    if expected_status == 200:
        assert response.json() == {"role": role}
