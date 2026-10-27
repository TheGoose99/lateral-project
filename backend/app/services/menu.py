from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.models import MenuCategory, MenuItem, Restaurant, User
from app.schemas.restaurant import (
    MenuCategoryCreateRequest,
    MenuCategoryUpdateRequest,
    MenuItemCreateRequest,
    MenuItemUpdateRequest,
    RestaurantMenuResponse,
)


def list_managed_restaurants(db: Session, user: User) -> list[Restaurant]:
    statement = select(Restaurant).order_by(Restaurant.name)
    if user.role == "staff":
        if user.restaurant_id is None:
            return []
        statement = statement.where(Restaurant.id == user.restaurant_id)
    return list(db.scalars(statement).all())


def require_managed_restaurant(db: Session, user: User, restaurant_id: UUID) -> Restaurant:
    if user.role == "staff":
        if user.restaurant_id is None or user.restaurant_id != restaurant_id:
            raise AppError(status.HTTP_404_NOT_FOUND, "Restaurant not found")

    restaurant = db.get(Restaurant, restaurant_id)
    if restaurant is None:
        raise AppError(status.HTTP_404_NOT_FOUND, "Restaurant not found")
    return restaurant


def get_managed_menu(db: Session, user: User, restaurant_id: UUID) -> RestaurantMenuResponse:
    restaurant = require_managed_restaurant(db, user, restaurant_id)
    loaded = db.scalar(
        select(Restaurant)
        .where(Restaurant.id == restaurant.id)
        .options(selectinload(Restaurant.categories).selectinload(MenuCategory.items))
    )
    assert loaded is not None

    categories = []
    for category in sorted(loaded.categories, key=lambda item: (item.sort_order, item.name)):
        items = sorted(category.items, key=lambda item: item.name)
        categories.append(
            {
                "id": category.id,
                "name": category.name,
                "sort_order": category.sort_order,
                "items": items,
            }
        )

    return RestaurantMenuResponse(
        id=loaded.id,
        name=loaded.name,
        slug=loaded.slug,
        description=loaded.description,
        address=loaded.address,
        phone=loaded.phone,
        categories=categories,
    )


def create_category(
    db: Session,
    user: User,
    restaurant_id: UUID,
    request: MenuCategoryCreateRequest,
) -> MenuCategory:
    restaurant = require_managed_restaurant(db, user, restaurant_id)
    category = MenuCategory(
        restaurant_id=restaurant.id,
        name=request.name.strip(),
        sort_order=request.sort_order,
    )
    db.add(category)
    try:
        db.flush()
    except IntegrityError as exc:
        raise AppError(
            status.HTTP_409_CONFLICT,
            "A category with this name already exists",
        ) from exc
    return category


def update_category(
    db: Session,
    user: User,
    category_id: UUID,
    request: MenuCategoryUpdateRequest,
) -> MenuCategory:
    category = _get_managed_category(db, user, category_id)
    if request.name is not None:
        category.name = request.name.strip()
    if request.sort_order is not None:
        category.sort_order = request.sort_order
    try:
        db.flush()
    except IntegrityError as exc:
        raise AppError(
            status.HTTP_409_CONFLICT,
            "A category with this name already exists",
        ) from exc
    return category


def delete_category(db: Session, user: User, category_id: UUID) -> None:
    category = _get_managed_category(db, user, category_id)
    item_count = len(category.items)
    if item_count > 0:
        raise AppError(
            status.HTTP_409_CONFLICT,
            "Remove or move menu items before deleting this category",
        )
    db.delete(category)
    db.flush()


def create_item(
    db: Session,
    user: User,
    category_id: UUID,
    request: MenuItemCreateRequest,
) -> MenuItem:
    category = _get_managed_category(db, user, category_id)
    item = MenuItem(
        category_id=category.id,
        name=request.name.strip(),
        description=request.description,
        price=request.price,
        is_available=request.is_available,
    )
    db.add(item)
    db.flush()
    return item


def update_item(
    db: Session,
    user: User,
    item_id: UUID,
    request: MenuItemUpdateRequest,
) -> MenuItem:
    item = _get_managed_item(db, user, item_id)
    if request.name is not None:
        item.name = request.name.strip()
    if request.description is not None:
        item.description = request.description
    if request.price is not None:
        item.price = request.price
    if request.is_available is not None:
        item.is_available = request.is_available
    if request.category_id is not None:
        new_category = _get_managed_category(db, user, request.category_id)
        item.category_id = new_category.id
    db.flush()
    return item


def delete_item(db: Session, user: User, item_id: UUID) -> None:
    item = _get_managed_item(db, user, item_id)
    db.delete(item)
    db.flush()


def _get_managed_category(db: Session, user: User, category_id: UUID) -> MenuCategory:
    category = db.scalar(
        select(MenuCategory)
        .where(MenuCategory.id == category_id)
        .options(selectinload(MenuCategory.items))
    )
    if category is None:
        raise AppError(status.HTTP_404_NOT_FOUND, "Category not found")
    require_managed_restaurant(db, user, category.restaurant_id)
    return category


def _get_managed_item(db: Session, user: User, item_id: UUID) -> MenuItem:
    item = db.scalar(
        select(MenuItem)
        .options(selectinload(MenuItem.category))
        .where(MenuItem.id == item_id)
    )
    if item is None:
        raise AppError(status.HTTP_404_NOT_FOUND, "Menu item not found")
    require_managed_restaurant(db, user, item.category.restaurant_id)
    return item
