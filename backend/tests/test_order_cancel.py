from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import MenuCategory, MenuItem, Restaurant, User

PASSWORD = "correct-horse-battery-staple"


def login_as(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def create_menu_item(db: Session) -> tuple[Restaurant, MenuItem]:
    restaurant = Restaurant(
        name=f"Restaurant {uuid4().hex[:8]}",
        slug=f"cancel-{uuid4().hex}",
        address="Test Street 1",
    )
    category = MenuCategory(name="Main courses", restaurant=restaurant)
    item = MenuItem(
        name="Test Burger",
        price=Decimal("25.00"),
        is_available=True,
        category=category,
    )
    db.add(restaurant)
    db.flush()
    return restaurant, item


def place_order(client: TestClient, token: str, restaurant: Restaurant, item: MenuItem) -> dict:
    response = client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "restaurant_id": str(restaurant.id),
            "items": [{"menu_item_id": str(item.id), "quantity": 1}],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_customer_can_cancel_pending_order(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant, item = create_menu_item(db_session)
    token = login_as(auth_client, registered_user["email"])
    order = place_order(auth_client, token, restaurant, item)

    response = auth_client.post(
        f"/api/v1/orders/{order['id']}/cancel",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "Changed my mind"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "cancelled"
    assert body["cancellation_reason"] == "Changed my mind"
    assert any(
        entry["to_status"] == "cancelled" and entry["reason"] == "Changed my mind"
        for entry in body["status_history"]
    )


def test_customer_cancel_requires_reason(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant, item = create_menu_item(db_session)
    token = login_as(auth_client, registered_user["email"])
    order = place_order(auth_client, token, restaurant, item)

    response = auth_client.post(
        f"/api/v1/orders/{order['id']}/cancel",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "   "},
    )

    assert response.status_code == 422


def test_customer_cannot_cancel_another_customers_order(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant, item = create_menu_item(db_session)
    token = login_as(auth_client, registered_user["email"])
    order = place_order(auth_client, token, restaurant, item)

    other_email = f"other-{uuid4().hex[:8]}@example.com"
    registration = auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": other_email,
            "password": PASSWORD,
            "full_name": "Other Customer",
        },
    )
    assert registration.status_code == 201
    other_token = login_as(auth_client, other_email)

    response = auth_client.post(
        f"/api/v1/orders/{order['id']}/cancel",
        headers={"Authorization": f"Bearer {other_token}"},
        json={"reason": "Not mine"},
    )

    assert response.status_code == 404


def test_customer_cannot_cancel_out_for_delivery_order(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant, item = create_menu_item(db_session)
    token = login_as(auth_client, registered_user["email"])
    order = place_order(auth_client, token, restaurant, item)

    user = db_session.query(User).filter(User.email == registered_user["email"]).one()
    user.role = "staff"
    user.restaurant_id = restaurant.id
    db_session.flush()
    staff_token = login_as(auth_client, registered_user["email"])

    for new_status in ("accepted", "preparing", "out_for_delivery"):
        response = auth_client.patch(
            f"/api/v1/orders/{order['id']}/status",
            headers={"Authorization": f"Bearer {staff_token}"},
            json={"status": new_status},
        )
        assert response.status_code == 200, response.text

    user.role = "customer"
    user.restaurant_id = None
    db_session.flush()
    customer_token = login_as(auth_client, registered_user["email"])

    response = auth_client.post(
        f"/api/v1/orders/{order['id']}/cancel",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"reason": "Too late"},
    )

    assert response.status_code == 409


def test_order_list_is_paginated(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant, item = create_menu_item(db_session)
    token = login_as(auth_client, registered_user["email"])
    first = place_order(auth_client, token, restaurant, item)
    second = place_order(auth_client, token, restaurant, item)

    response = auth_client.get(
        "/api/v1/orders?limit=1&offset=0",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 2
    assert body["limit"] == 1
    assert body["offset"] == 0
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] in {first["id"], second["id"]}
