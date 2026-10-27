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


def create_restaurant(db: Session, name: str | None = None) -> Restaurant:
    restaurant = Restaurant(
        name=name or f"Restaurant {uuid4().hex[:8]}",
        slug=f"menu-{uuid4().hex}",
        address="Test Street 1",
    )
    db.add(restaurant)
    db.flush()
    return restaurant


def promote(db: Session, email: str, role: str, restaurant_id=None) -> None:
    user = db.query(User).filter(User.email == email).one()
    user.role = role
    user.restaurant_id = restaurant_id
    db.flush()


def test_staff_can_manage_menu_for_assigned_restaurant(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant = create_restaurant(db_session)
    promote(db_session, registered_user["email"], "staff", restaurant.id)
    token = login_as(auth_client, registered_user["email"])
    headers = {"Authorization": f"Bearer {token}"}

    created = auth_client.post(
        f"/api/v1/staff/restaurants/{restaurant.id}/categories",
        headers=headers,
        json={"name": "Burgers", "sort_order": 1},
    )
    assert created.status_code == 201, created.text
    category_id = created.json()["id"]

    item_response = auth_client.post(
        f"/api/v1/staff/categories/{category_id}/items",
        headers=headers,
        json={
            "name": "Hidden Burger",
            "description": "Only staff can see this until it is available",
            "price": "29.50",
            "is_available": False,
        },
    )
    assert item_response.status_code == 201, item_response.text
    item_id = item_response.json()["id"]

    public_menu = auth_client.get(f"/api/v1/restaurants/{restaurant.id}/menu")
    assert public_menu.status_code == 200
    assert public_menu.json()["categories"][0]["items"] == []

    staff_menu = auth_client.get(
        f"/api/v1/staff/restaurants/{restaurant.id}/menu",
        headers=headers,
    )
    assert staff_menu.status_code == 200, staff_menu.text
    items = staff_menu.json()["categories"][0]["items"]
    assert items[0]["name"] == "Hidden Burger"
    assert items[0]["is_available"] is False

    available = auth_client.patch(
        f"/api/v1/staff/items/{item_id}",
        headers=headers,
        json={"is_available": True},
    )
    assert available.status_code == 200
    public_menu = auth_client.get(f"/api/v1/restaurants/{restaurant.id}/menu")
    assert public_menu.json()["categories"][0]["items"][0]["name"] == "Hidden Burger"


def test_staff_cannot_manage_another_restaurants_menu(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    assigned = create_restaurant(db_session)
    other = create_restaurant(db_session)
    other_category = MenuCategory(name="Sides", restaurant=other)
    other_item = MenuItem(
        name="Fries",
        price=Decimal("10.00"),
        category=other_category,
    )
    db_session.add(other_item)
    db_session.flush()

    promote(db_session, registered_user["email"], "staff", assigned.id)
    token = login_as(auth_client, registered_user["email"])
    headers = {"Authorization": f"Bearer {token}"}

    create_response = auth_client.post(
        f"/api/v1/staff/restaurants/{other.id}/categories",
        headers=headers,
        json={"name": "Intruder"},
    )
    menu_response = auth_client.get(
        f"/api/v1/staff/restaurants/{other.id}/menu",
        headers=headers,
    )
    item_response = auth_client.patch(
        f"/api/v1/staff/items/{other_item.id}",
        headers=headers,
        json={"is_available": False},
    )

    assert create_response.status_code == 404
    assert menu_response.status_code == 404
    assert item_response.status_code == 404


def test_admin_can_manage_any_restaurant_menu(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant = create_restaurant(db_session)
    promote(db_session, registered_user["email"], "admin")
    token = login_as(auth_client, registered_user["email"])
    headers = {"Authorization": f"Bearer {token}"}

    restaurants = auth_client.get("/api/v1/staff/restaurants", headers=headers)
    assert restaurants.status_code == 200
    assert str(restaurant.id) in {entry["id"] for entry in restaurants.json()}

    created = auth_client.post(
        f"/api/v1/staff/restaurants/{restaurant.id}/categories",
        headers=headers,
        json={"name": "Drinks"},
    )
    assert created.status_code == 201, created.text


def test_category_delete_rejected_when_items_exist(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant = create_restaurant(db_session)
    category = MenuCategory(name="Mains", restaurant=restaurant)
    item = MenuItem(name="Soup", price=Decimal("12.00"), category=category)
    db_session.add(item)
    db_session.flush()

    promote(db_session, registered_user["email"], "staff", restaurant.id)
    token = login_as(auth_client, registered_user["email"])

    response = auth_client.delete(
        f"/api/v1/staff/categories/{category.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 409

    auth_client.delete(
        f"/api/v1/staff/items/{item.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    empty_delete = auth_client.delete(
        f"/api/v1/staff/categories/{category.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert empty_delete.status_code == 204


def test_customer_cannot_use_staff_menu_endpoints(
    auth_client: TestClient,
    db_session: Session,
    registered_user: dict[str, str],
) -> None:
    restaurant = create_restaurant(db_session)
    token = login_as(auth_client, registered_user["email"])
    response = auth_client.get(
        f"/api/v1/staff/restaurants/{restaurant.id}/menu",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
