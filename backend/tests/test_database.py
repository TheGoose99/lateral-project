import os
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import MenuCategory, MenuItem, Order, Restaurant, User


@pytest.fixture()
def db_session():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.fail("DATABASE_URL must point to the dedicated test database")

    engine = create_engine(database_url, pool_pre_ping=True)
    connection = engine.connect()
    transaction = connection.begin()

    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        engine.dispose()


def test_restaurant_menu_relationships(db_session: Session):
    restaurant = Restaurant(
        name="Integration Test Bistro",
        slug=f"test-bistro-{uuid4().hex[:8]}",
        address="Test address",
    )
    category = MenuCategory(name="Main courses", restaurant=restaurant)
    MenuItem(
        name="Test pasta",
        price=Decimal("12.50"),
        category=category,
    )

    db_session.add(restaurant)
    db_session.flush()

    found = db_session.scalar(select(Restaurant).where(Restaurant.id == restaurant.id))

    assert found is not None
    assert found.categories[0].name == "Main courses"
    assert found.categories[0].items[0].name == "Test pasta"
    assert found.categories[0].items[0].price == Decimal("12.50")


def test_database_rejects_invalid_user_role(db_session: Session):
    restaurant = Restaurant(
        name="Constraint Test Bistro",
        slug=f"constraint-test-{uuid4().hex[:8]}",
        address="Test address",
    )
    db_session.add(restaurant)
    db_session.flush()

    user = User(
        email=f"test-{uuid4().hex}@example.com",
        password_hash="not-a-real-hash",
        full_name="Test User",
        role="superuser",
    )
    db_session.add(user)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_database_rejects_negative_menu_price(db_session: Session):
    restaurant = Restaurant(
        name="Price Test Bistro",
        slug=f"price-test-{uuid4().hex[:8]}",
        address="Test address",
    )
    category = MenuCategory(name="Mains", restaurant=restaurant)
    db_session.add(restaurant)
    db_session.flush()

    db_session.add(
        MenuItem(
            name="Invalid item",
            price=Decimal("-1.00"),
            category=category,
        )
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_database_rejects_invalid_order_status(db_session: Session):
    restaurant = Restaurant(
        name="Status Test Bistro",
        slug=f"status-test-{uuid4().hex[:8]}",
        address="Test address",
    )
    customer = User(
        email=f"customer-{uuid4().hex}@example.com",
        password_hash="not-a-real-hash",
        full_name="Test Customer",
    )
    db_session.add_all([restaurant, customer])
    db_session.flush()

    order = Order(
        customer_id=customer.id,
        restaurant_id=restaurant.id,
        status="teleported",
        total_amount=Decimal("10.00"),
    )
    db_session.add(order)

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_database_rejects_duplicate_restaurant_slug(db_session: Session):
    slug = f"duplicate-{uuid4().hex[:8]}"

    db_session.add(Restaurant(name="First", slug=slug, address="Address 1"))
    db_session.flush()

    db_session.add(Restaurant(name="Second", slug=slug, address="Address 2"))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_database_rejects_duplicate_user_email(db_session: Session):
    email = f"duplicate-{uuid4().hex}@example.com"

    db_session.add(User(email=email, password_hash="hash", full_name="First User"))
    db_session.flush()

    db_session.add(User(email=email, password_hash="hash", full_name="Second User"))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_database_rejects_email_with_different_capitalization(db_session: Session):
    email = f"User-{uuid4().hex[:8]}@Example.com"

    db_session.add(
        User(
            email=email,
            password_hash="hash",
            full_name="First User",
        )
    )
    db_session.flush()

    db_session.add(
        User(
            email=email.lower(),
            password_hash="hash",
            full_name="Second User",
        )
    )

    with pytest.raises(IntegrityError):
        db_session.flush()
