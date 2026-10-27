from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.menu_category import MenuCategory
from app.models.restaurant import Restaurant
from app.schemas.restaurant import RestaurantMenuResponse, RestaurantSummary

router = APIRouter(prefix="/restaurants", tags=["restaurants"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[RestaurantSummary])
def list_restaurants(db: DbSession) -> list[Restaurant]:
    statement = select(Restaurant).where(Restaurant.is_active.is_(True)).order_by(Restaurant.name)
    return list(db.scalars(statement).all())


@router.get("/{restaurant_id}", response_model=RestaurantSummary)
def get_restaurant(restaurant_id: UUID, db: DbSession) -> Restaurant:
    restaurant = db.scalar(
        select(Restaurant).where(
            Restaurant.id == restaurant_id,
            Restaurant.is_active.is_(True),
        )
    )
    if restaurant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found",
        )
    return restaurant


@router.get("/{restaurant_id}/menu", response_model=RestaurantMenuResponse)
def get_restaurant_menu(restaurant_id: UUID, db: DbSession) -> RestaurantMenuResponse:
    statement = (
        select(Restaurant)
        .where(
            Restaurant.id == restaurant_id,
            Restaurant.is_active.is_(True),
        )
        .options(selectinload(Restaurant.categories).selectinload(MenuCategory.items))
    )
    restaurant = db.scalar(statement)

    if restaurant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found",
        )

    categories = []
    for category in sorted(restaurant.categories, key=lambda item: (item.sort_order, item.name)):
        available_items = sorted(
            (item for item in category.items if item.is_available),
            key=lambda item: item.name,
        )
        categories.append(
            {
                "id": category.id,
                "name": category.name,
                "sort_order": category.sort_order,
                "items": available_items,
            }
        )

    return RestaurantMenuResponse(
        id=restaurant.id,
        name=restaurant.name,
        slug=restaurant.slug,
        description=restaurant.description,
        address=restaurant.address,
        phone=restaurant.phone,
        categories=categories,
    )
