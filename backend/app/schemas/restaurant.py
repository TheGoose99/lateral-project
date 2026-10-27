from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RestaurantSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    description: str | None
    address: str
    phone: str | None


class MenuItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    price: float
    is_available: bool


class MenuCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    sort_order: int
    items: list[MenuItemResponse] = Field(default_factory=list)


class RestaurantMenuResponse(RestaurantSummary):
    categories: list[MenuCategoryResponse] = Field(default_factory=list)


class MenuCategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    sort_order: int = Field(default=0, ge=0, le=10_000)


class MenuCategoryUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    sort_order: int | None = Field(default=None, ge=0, le=10_000)


class MenuItemCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    is_available: bool = True


class MenuItemUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    is_available: bool | None = None
    category_id: UUID | None = None
