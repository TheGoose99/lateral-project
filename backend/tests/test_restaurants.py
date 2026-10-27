from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import MenuCategory, MenuItem, Restaurant


def create_restaurant(
    db_session: Session,
    *,
    name: str = "Test Bistro",
    is_active: bool = True,
) -> Restaurant:
    restaurant = Restaurant(
        name=name,
        slug=f"test-bistro-{uuid4().hex[:8]}",
        description="A test restaurant",
        address="Test Street 1",
        phone="0700000000",
        is_active=is_active,
    )
    db_session.add(restaurant)
    db_session.flush()
    return restaurant


def test_list_restaurants_returns_only_active_restaurants(
    auth_client: TestClient,
    db_session: Session,
) -> None:
    active = create_restaurant(db_session, name="Active Bistro")
    create_restaurant(db_session, name="Inactive Bistro", is_active=False)

    response = auth_client.get("/api/v1/restaurants")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(active.id)]
    assert response.json()[0]["name"] == "Active Bistro"


def test_get_restaurant_returns_restaurant_details(
    auth_client: TestClient,
    db_session: Session,
) -> None:
    restaurant = create_restaurant(db_session)

    response = auth_client.get(f"/api/v1/restaurants/{restaurant.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(restaurant.id)
    assert response.json()["name"] == restaurant.name
    assert response.json()["address"] == restaurant.address


def test_get_restaurant_returns_404_for_missing_restaurant(
    auth_client: TestClient,
) -> None:
    response = auth_client.get(f"/api/v1/restaurants/{uuid4()}")

    assert response.status_code == 404


def test_get_restaurant_returns_404_for_inactive_restaurant(
    auth_client: TestClient,
    db_session: Session,
) -> None:
    restaurant = create_restaurant(db_session, is_active=False)

    response = auth_client.get(f"/api/v1/restaurants/{restaurant.id}")

    assert response.status_code == 404


def test_restaurant_menu_sorts_categories_and_items_and_hides_unavailable(
    auth_client: TestClient,
    db_session: Session,
) -> None:
    restaurant = create_restaurant(db_session)

    sides = MenuCategory(
        name="Sides",
        sort_order=2,
        restaurant=restaurant,
    )
    mains = MenuCategory(
        name="Main courses",
        sort_order=1,
        restaurant=restaurant,
    )

    db_session.add_all([sides, mains])
    db_session.flush()

    db_session.add_all(
        [
            MenuItem(
                name="Zucchini fries",
                price=Decimal("12.50"),
                category=sides,
            ),
            MenuItem(
                name="Burger",
                price=Decimal("35.00"),
                category=mains,
            ),
            MenuItem(
                name="Pasta",
                price=Decimal("29.90"),
                category=mains,
            ),
            MenuItem(
                name="Unavailable dish",
                price=Decimal("20.00"),
                category=mains,
                is_available=False,
            ),
        ]
    )
    db_session.flush()

    response = auth_client.get(f"/api/v1/restaurants/{restaurant.id}/menu")

    assert response.status_code == 200

    body = response.json()
    assert body["id"] == str(restaurant.id)
    assert [category["name"] for category in body["categories"]] == [
        "Main courses",
        "Sides",
    ]

    main_items = body["categories"][0]["items"]
    assert [item["name"] for item in main_items] == ["Burger", "Pasta"]
    assert main_items[0]["price"] == 35.0
    assert all(item["is_available"] for item in main_items)


def test_restaurant_menu_returns_404_for_missing_restaurant(
    auth_client: TestClient,
) -> None:
    response = auth_client.get(f"/api/v1/restaurants/{uuid4()}/menu")

    assert response.status_code == 404
