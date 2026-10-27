from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OrderItemCreate(BaseModel):
    menu_item_id: UUID
    quantity: int = Field(ge=1, le=99)


class OrderCreateRequest(BaseModel):
    restaurant_id: UUID
    items: list[OrderItemCreate] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def validate_unique_items(self) -> "OrderCreateRequest":
        item_ids = [item.menu_item_id for item in self.items]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("Each menu item may appear only once")
        return self


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    menu_item_id: UUID | None
    name_snapshot: str
    unit_price_snapshot: Decimal
    quantity: int
    line_total: Decimal


class OrderStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    from_status: str | None
    to_status: str
    reason: str | None
    created_at: datetime


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    restaurant_id: UUID
    restaurant_name: str
    status: str
    total_amount: Decimal
    currency: str
    cancellation_reason: str | None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse]
    status_history: list[OrderStatusHistoryResponse]


class OrderCancelRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def strip_reason(self) -> "OrderCancelRequest":
        self.reason = self.reason.strip()
        if not self.reason:
            raise ValueError("A reason is required to cancel an order")
        return self


class PaginatedOrderResponse(BaseModel):
    items: list[OrderResponse]
    total: int
    limit: int
    offset: int


class OrderStatusUpdateRequest(BaseModel):
    status: Literal[
        "accepted",
        "preparing",
        "out_for_delivery",
        "delivered",
        "cancelled",
    ]
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_cancellation_reason(self) -> "OrderStatusUpdateRequest":
        if self.status == "cancelled" and not self.reason:
            raise ValueError("A reason is required to cancel an order")

        if self.reason is not None:
            self.reason = self.reason.strip()
            if not self.reason:
                raise ValueError("Reason cannot be blank")

        return self
