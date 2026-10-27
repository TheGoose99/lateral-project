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


def create_order(
    client: TestClient,
    token: str,
    restaurant: Restaurant,
    item: MenuItem,
) -> dict:
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


def create_menu_item(
    db: Session,
    name: str = "Test Burger",
) -> tuple[Restaurant, MenuItem]:
    restaurant = Restaurant(
        name=f"Restaurant {uuid4().hex[:8]}",
        slug=f"management-{uuid4().hex}",
        address="Test Street 1",
    )
    category = MenuCategory(name="Main courses", restaurant=restaurant)
    item = MenuItem(
        name=name,
        price=Decimal("25.00"),
        is_available=True,
        category=category,
    )
    db.add(restaurant)
    db.flush()
    return restaurant, item


def promote_user(
    db: Session,
    email: str,
    role: str,
    restaurant_id=None,
) -> None:
    user = db.query(User).filter(User.email == email).one()
    user.role = role
    user.restaurant_id = restaurant_id
    db.flush()


def test_staff_queue_only_contains_assigned_restaurants(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant_a, item_a = create_menu_item(db_session)
    restaurant_b, item_b = create_menu_item(db_session)

    customer_token = login_as(auth_client, registered_user["email"])
    order_a = create_order(auth_client, customer_token, restaurant_a, item_a)
    create_order(auth_client, customer_token, restaurant_b, item_b)

    promote_user(
        db_session,
        registered_user["email"],
        "staff",
        restaurant_a.id,
    )
    staff_token = login_as(auth_client, registered_user["email"])

    response = auth_client.get(
        "/api/v1/orders/staff/queue",
        headers={"Authorization": f"Bearer {staff_token}"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert [order["id"] for order in body["items"]] == [order_a["id"]]


def test_staff_can_advance_order_and_history_is_recorded(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant, item = create_menu_item(db_session)
    customer_token = login_as(auth_client, registered_user["email"])
    order = create_order(auth_client, customer_token, restaurant, item)

    promote_user(
        db_session,
        registered_user["email"],
        "staff",
        restaurant.id,
    )
    staff_token = login_as(auth_client, registered_user["email"])

    response = auth_client.patch(
        f"/api/v1/orders/{order['id']}/status",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"status": "accepted"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "accepted"
    assert any(
        entry["from_status"] == "pending" and entry["to_status"] == "accepted"
        for entry in body["status_history"]
    )


def test_staff_cannot_update_another_restaurants_order(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant_a, item_a = create_menu_item(db_session)
    restaurant_b, item_b = create_menu_item(db_session)
    customer_token = login_as(auth_client, registered_user["email"])
    order_b = create_order(auth_client, customer_token, restaurant_b, item_b)

    promote_user(
        db_session,
        registered_user["email"],
        "staff",
        restaurant_a.id,
    )
    staff_token = login_as(auth_client, registered_user["email"])

    response = auth_client.patch(
        f"/api/v1/orders/{order_b['id']}/status",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"status": "accepted"},
    )

    assert response.status_code == 404


def test_invalid_status_transition_returns_conflict(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant, item = create_menu_item(db_session)
    customer_token = login_as(auth_client, registered_user["email"])
    order = create_order(auth_client, customer_token, restaurant, item)

    promote_user(
        db_session,
        registered_user["email"],
        "staff",
        restaurant.id,
    )
    staff_token = login_as(auth_client, registered_user["email"])

    headers = {"Authorization": f"Bearer {staff_token}"}
    for illegal_status in ("out_for_delivery", "delivered"):
        response = auth_client.patch(
            f"/api/v1/orders/{order['id']}/status",
            headers=headers,
            json={"status": illegal_status},
        )
        assert response.status_code == 409


def test_cancellation_requires_a_reason(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant, item = create_menu_item(db_session)
    customer_token = login_as(auth_client, registered_user["email"])
    order = create_order(auth_client, customer_token, restaurant, item)

    promote_user(
        db_session,
        registered_user["email"],
        "staff",
        restaurant.id,
    )
    staff_token = login_as(auth_client, registered_user["email"])

    response = auth_client.patch(
        f"/api/v1/orders/{order['id']}/status",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"status": "cancelled"},
    )

    assert response.status_code == 422


def test_admin_can_list_orders_across_restaurants(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant_a, item_a = create_menu_item(db_session)
    restaurant_b, item_b = create_menu_item(db_session)
    customer_token = login_as(auth_client, registered_user["email"])
    order_a = create_order(auth_client, customer_token, restaurant_a, item_a)
    order_b = create_order(auth_client, customer_token, restaurant_b, item_b)

    promote_user(db_session, registered_user["email"], "admin")
    admin_token = login_as(auth_client, registered_user["email"])

    response = auth_client.get(
        "/api/v1/orders/staff/queue",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    returned_ids = {order["id"] for order in body["items"]}
    assert {order_a["id"], order_b["id"]}.issubset(returned_ids)
    assert body["total"] >= 2


def test_customer_cannot_access_staff_management_endpoints(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant, item = create_menu_item(db_session)
    token = login_as(auth_client, registered_user["email"])
    order = create_order(auth_client, token, restaurant, item)
    headers = {"Authorization": f"Bearer {token}"}

    queue_response = auth_client.get(
        "/api/v1/orders/staff/queue",
        headers=headers,
    )
    status_response = auth_client.patch(
        f"/api/v1/orders/{order['id']}/status",
        headers=headers,
        json={"status": "accepted"},
    )

    assert queue_response.status_code == 403
    assert status_response.status_code == 403


def test_unassigned_staff_cannot_manage_orders(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant, item = create_menu_item(db_session)
    customer_token = login_as(auth_client, registered_user["email"])
    order = create_order(auth_client, customer_token, restaurant, item)

    promote_user(db_session, registered_user["email"], "staff")
    staff_token = login_as(auth_client, registered_user["email"])
    headers = {"Authorization": f"Bearer {staff_token}"}

    queue_response = auth_client.get(
        "/api/v1/orders/staff/queue",
        headers=headers,
    )
    status_response = auth_client.patch(
        f"/api/v1/orders/{order['id']}/status",
        headers=headers,
        json={"status": "accepted"},
    )

    assert queue_response.status_code == 200
    assert queue_response.json()["items"] == []
    assert queue_response.json()["total"] == 0
    assert status_response.status_code == 404


def test_order_completes_spec_flow_skipping_preparing(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant, item = create_menu_item(db_session)
    customer_token = login_as(auth_client, registered_user["email"])
    order = create_order(auth_client, customer_token, restaurant, item)

    promote_user(
        db_session,
        registered_user["email"],
        "staff",
        restaurant.id,
    )
    staff_token = login_as(auth_client, registered_user["email"])
    headers = {"Authorization": f"Bearer {staff_token}"}

    for new_status in ("accepted", "out_for_delivery", "delivered"):
        response = auth_client.patch(
            f"/api/v1/orders/{order['id']}/status",
            headers=headers,
            json={"status": new_status},
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == new_status

    history = response.json()["status_history"]
    assert [entry["to_status"] for entry in history] == [
        "pending",
        "accepted",
        "out_for_delivery",
        "delivered",
    ]


def test_order_completes_full_lifecycle_with_ordered_history(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant, item = create_menu_item(db_session)
    customer_token = login_as(auth_client, registered_user["email"])
    order = create_order(auth_client, customer_token, restaurant, item)

    promote_user(
        db_session,
        registered_user["email"],
        "staff",
        restaurant.id,
    )
    staff_token = login_as(auth_client, registered_user["email"])
    headers = {"Authorization": f"Bearer {staff_token}"}

    transitions = [
        ("accepted", "pending"),
        ("preparing", "accepted"),
        ("out_for_delivery", "preparing"),
        ("delivered", "out_for_delivery"),
    ]

    for new_status, previous_status in transitions:
        response = auth_client.patch(
            f"/api/v1/orders/{order['id']}/status",
            headers=headers,
            json={"status": new_status},
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == new_status

        assert any(
            entry["from_status"] == previous_status
            and entry["to_status"] == new_status
            for entry in body["status_history"]
        )

    history = body["status_history"]
    assert [entry["to_status"] for entry in history] == [
        "pending",
        "accepted",
        "preparing",
        "out_for_delivery",
        "delivered",
    ]
