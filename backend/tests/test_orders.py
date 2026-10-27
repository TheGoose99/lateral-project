from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import MenuCategory, MenuItem, Restaurant


def login_as(
    client: TestClient,
    email: str,
) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "correct-horse-battery-staple",
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def create_menu_item(
    db_session: Session,
    *,
    restaurant_name: str = "Order Test Bistro",
    name: str = "Test Burger",
    price: Decimal = Decimal("25.00"),
    is_available: bool = True,
) -> tuple[Restaurant, MenuItem]:
    restaurant = Restaurant(
        name=restaurant_name,
        slug=f"order-test-{uuid4().hex[:8]}",
        address="Test Street 1",
    )
    category = MenuCategory(name="Main courses", restaurant=restaurant)
    item = MenuItem(
        name=name,
        price=price,
        is_available=is_available,
        category=category,
    )
    db_session.add(restaurant)
    db_session.flush()
    return restaurant, item


def test_customer_can_place_order_with_server_calculated_total(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant, item = create_menu_item(db_session)
    db_session.add(
        MenuItem(
            name="Test Fries",
            price=Decimal("10.50"),
            category=item.category,
        )
    )
    db_session.flush()

    token = login_as(auth_client, registered_user["email"])
    response = auth_client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "restaurant_id": str(restaurant.id),
            "items": [
                {"menu_item_id": str(item.id), "quantity": 2},
                {
                    "menu_item_id": str(
                        next(
                            menu_item.id
                            for menu_item in item.category.items
                            if menu_item.name == "Test Fries"
                        )
                    ),
                    "quantity": 1,
                },
            ],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert Decimal(body["total_amount"]) == Decimal("60.50")
    assert body["restaurant_name"] == restaurant.name
    assert body["status"] == "pending"
    assert body["currency"] == "RON"
    assert len(body["items"]) == 2
    assert body["status_history"][0]["from_status"] is None
    assert body["status_history"][0]["to_status"] == "pending"


def test_order_preserves_item_name_and_price_snapshots(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant, item = create_menu_item(db_session)
    token = login_as(auth_client, registered_user["email"])

    response = auth_client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "restaurant_id": str(restaurant.id),
            "items": [{"menu_item_id": str(item.id), "quantity": 2}],
        },
    )

    assert response.status_code == 201
    order_id = response.json()["id"]
    assert response.json()["items"][0]["name_snapshot"] == "Test Burger"
    assert Decimal(response.json()["items"][0]["unit_price_snapshot"]) == Decimal("25.00")

    item.name = "Renamed Burger"
    item.price = Decimal("99.00")
    db_session.flush()

    order_response = auth_client.get(
        f"/api/v1/orders/{order_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert order_response.status_code == 200
    body = order_response.json()
    assert Decimal(body["total_amount"]) == Decimal("50.00")
    assert body["items"][0]["name_snapshot"] == "Test Burger"
    assert Decimal(body["items"][0]["unit_price_snapshot"]) == Decimal("25.00")


def test_order_rejects_unavailable_menu_item(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant, item = create_menu_item(db_session, is_available=False)
    token = login_as(auth_client, registered_user["email"])

    response = auth_client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "restaurant_id": str(restaurant.id),
            "items": [{"menu_item_id": str(item.id), "quantity": 1}],
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "One or more menu items are unavailable"


def test_order_rejects_item_from_another_restaurant(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant_a, _ = create_menu_item(db_session, restaurant_name="Bistro A")
    _, item_b = create_menu_item(db_session, restaurant_name="Bistro B")
    token = login_as(auth_client, registered_user["email"])

    response = auth_client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "restaurant_id": str(restaurant_a.id),
            "items": [{"menu_item_id": str(item_b.id), "quantity": 1}],
        },
    )

    assert response.status_code == 422
    assert "do not belong" in response.json()["detail"]


def test_order_creation_requires_authentication(
    auth_client: TestClient,
    db_session: Session,
) -> None:
    restaurant, item = create_menu_item(db_session)

    response = auth_client.post(
        "/api/v1/orders",
        json={
            "restaurant_id": str(restaurant.id),
            "items": [{"menu_item_id": str(item.id), "quantity": 1}],
        },
    )

    assert response.status_code == 401


def test_customer_cannot_read_another_customers_order(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant, item = create_menu_item(db_session)
    first_token = login_as(auth_client, registered_user["email"])

    order_response = auth_client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {first_token}"},
        json={
            "restaurant_id": str(restaurant.id),
            "items": [{"menu_item_id": str(item.id), "quantity": 1}],
        },
    )
    assert order_response.status_code == 201
    order_id = order_response.json()["id"]

    second_email = f"other-{uuid4().hex[:8]}@example.com"
    registration = auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": second_email,
            "password": "correct-horse-battery-staple",
            "full_name": "Other Customer",
        },
    )
    assert registration.status_code == 201

    second_token = login_as(auth_client, second_email)
    response = auth_client.get(
        f"/api/v1/orders/{order_id}",
        headers={"Authorization": f"Bearer {second_token}"},
    )

    assert response.status_code == 404


def test_customer_order_list_contains_only_their_orders(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant, item = create_menu_item(db_session)
    first_token = login_as(auth_client, registered_user["email"])

    create_response = auth_client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {first_token}"},
        json={
            "restaurant_id": str(restaurant.id),
            "items": [{"menu_item_id": str(item.id), "quantity": 1}],
        },
    )
    assert create_response.status_code == 201

    second_email = f"other-{uuid4().hex[:8]}@example.com"
    registration = auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": second_email,
            "password": "correct-horse-battery-staple",
            "full_name": "Other Customer",
        },
    )
    assert registration.status_code == 201

    second_token = login_as(auth_client, second_email)
    response = auth_client.get(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {second_token}"},
    )

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0


def test_idempotency_key_replays_same_order(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant, item = create_menu_item(db_session)
    token = login_as(auth_client, registered_user["email"])
    payload = {
        "restaurant_id": str(restaurant.id),
        "items": [{"menu_item_id": str(item.id), "quantity": 1}],
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": "checkout-abc-123",
    }

    first = auth_client.post("/api/v1/orders", headers=headers, json=payload)
    second = auth_client.post("/api/v1/orders", headers=headers, json=payload)

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]

    listed = auth_client.get(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert listed.json()["total"] == 1


def test_idempotency_key_rejects_different_body(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant, item = create_menu_item(db_session)
    token = login_as(auth_client, registered_user["email"])
    headers = {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": "checkout-conflict",
    }

    first = auth_client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "restaurant_id": str(restaurant.id),
            "items": [{"menu_item_id": str(item.id), "quantity": 1}],
        },
    )
    conflict = auth_client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "restaurant_id": str(restaurant.id),
            "items": [{"menu_item_id": str(item.id), "quantity": 2}],
        },
    )

    assert first.status_code == 201
    assert conflict.status_code == 409
    assert (
        conflict.json()["detail"]
        == "Idempotency key was already used with a different request"
    )
