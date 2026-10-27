from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models import MenuCategory
from app.models.user import User
from app.schemas.restaurant import (
    MenuCategoryCreateRequest,
    MenuCategoryResponse,
    MenuCategoryUpdateRequest,
    MenuItemCreateRequest,
    MenuItemResponse,
    MenuItemUpdateRequest,
    RestaurantMenuResponse,
    RestaurantSummary,
)
from app.services.menu import (
    create_category,
    create_item,
    delete_category,
    delete_item,
    get_managed_menu,
    list_managed_restaurants,
    update_category,
    update_item,
)

router = APIRouter(prefix="/staff", tags=["staff"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentManager = Annotated[User, Depends(require_role("staff", "admin"))]


def _commit(db: Session) -> None:
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


@router.get("/restaurants", response_model=list[RestaurantSummary])
def staff_restaurants(db: DbSession, manager: CurrentManager) -> list[RestaurantSummary]:
    return list_managed_restaurants(db, manager)


@router.get("/restaurants/{restaurant_id}/menu", response_model=RestaurantMenuResponse)
def staff_restaurant_menu(
    restaurant_id: UUID,
    db: DbSession,
    manager: CurrentManager,
) -> RestaurantMenuResponse:
    return get_managed_menu(db, manager, restaurant_id)


@router.post(
    "/restaurants/{restaurant_id}/categories",
    response_model=MenuCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def staff_create_category(
    restaurant_id: UUID,
    request: MenuCategoryCreateRequest,
    db: DbSession,
    manager: CurrentManager,
) -> MenuCategory:
    category = create_category(db, manager, restaurant_id, request)
    _commit(db)
    return db.get(MenuCategory, category.id)


@router.patch("/categories/{category_id}", response_model=MenuCategoryResponse)
def staff_update_category(
    category_id: UUID,
    request: MenuCategoryUpdateRequest,
    db: DbSession,
    manager: CurrentManager,
) -> MenuCategory:
    category = update_category(db, manager, category_id, request)
    _commit(db)
    return db.get(MenuCategory, category.id)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def staff_delete_category(
    category_id: UUID,
    db: DbSession,
    manager: CurrentManager,
) -> None:
    delete_category(db, manager, category_id)
    _commit(db)


@router.post(
    "/categories/{category_id}/items",
    response_model=MenuItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def staff_create_item(
    category_id: UUID,
    request: MenuItemCreateRequest,
    db: DbSession,
    manager: CurrentManager,
) -> MenuItemResponse:
    item = create_item(db, manager, category_id, request)
    _commit(db)
    return item


@router.patch("/items/{item_id}", response_model=MenuItemResponse)
def staff_update_item(
    item_id: UUID,
    request: MenuItemUpdateRequest,
    db: DbSession,
    manager: CurrentManager,
) -> MenuItemResponse:
    item = update_item(db, manager, item_id, request)
    _commit(db)
    return item


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def staff_delete_item(
    item_id: UUID,
    db: DbSession,
    manager: CurrentManager,
) -> None:
    delete_item(db, manager, item_id)
    _commit(db)
