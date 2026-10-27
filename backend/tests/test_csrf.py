from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from test_orders import create_menu_item, login_as


def test_cookie_mutation_without_csrf_is_forbidden(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant, item = create_menu_item(db_session)
    login_as(auth_client, registered_user["email"])

    response = auth_client.post(
        "/api/v1/orders",
        json={
            "restaurant_id": str(restaurant.id),
            "items": [{"menu_item_id": str(item.id), "quantity": 1}],
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "CSRF token missing or invalid"


def test_cookie_mutation_with_csrf_succeeds(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant, item = create_menu_item(db_session, restaurant_name="CSRF Bistro")
    login_as(auth_client, registered_user["email"])
    csrf = auth_client.cookies.get("takeaway_csrf")
    assert csrf

    response = auth_client.post(
        "/api/v1/orders",
        headers={"X-CSRF-Token": csrf},
        json={
            "restaurant_id": str(restaurant.id),
            "items": [{"menu_item_id": str(item.id), "quantity": 1}],
        },
    )

    assert response.status_code == 201
    assert Decimal(response.json()["total_amount"]) == Decimal("25.00")


def test_bearer_mutation_does_not_need_csrf(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant, item = create_menu_item(db_session, restaurant_name="Bearer Bistro")
    token = login_as(auth_client, registered_user["email"])

    response = auth_client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "restaurant_id": str(restaurant.id),
            "items": [{"menu_item_id": str(item.id), "quantity": 1}],
        },
    )

    assert response.status_code == 201


def test_cookie_mutation_rejects_foreign_origin(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant, item = create_menu_item(db_session, restaurant_name="Origin Bistro")
    login_as(auth_client, registered_user["email"])
    csrf = auth_client.cookies.get("takeaway_csrf")
    assert csrf

    response = auth_client.post(
        "/api/v1/orders",
        headers={
            "X-CSRF-Token": csrf,
            "Origin": "http://evil.example",
        },
        json={
            "restaurant_id": str(restaurant.id),
            "items": [{"menu_item_id": str(item.id), "quantity": 1}],
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid request origin"
