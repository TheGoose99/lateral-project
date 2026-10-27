from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.config import get_settings
from app.core.rate_limit import enforce_rate_limit
from app.db.session import get_db
from app.models.user import User
from app.schemas.order import (
    OrderCancelRequest,
    OrderCreateRequest,
    OrderResponse,
    OrderStatusUpdateRequest,
    PaginatedOrderResponse,
)
from app.services.orders import (
    cancel_customer_order,
    get_customer_order,
    get_managed_order,
    list_customer_orders,
    list_managed_orders,
    place_customer_order,
    update_order_status,
)

router = APIRouter(prefix="/orders", tags=["orders"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentCustomer = Annotated[User, Depends(require_role("customer"))]
CurrentManager = Annotated[
    User,
    Depends(require_role("staff", "admin")),
]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


def _commit(db: Session) -> None:
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def place_order(
    http_request: Request,
    request: OrderCreateRequest,
    db: DbSession,
    customer: CurrentCustomer,
    response: Response,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> OrderResponse:
    enforce_rate_limit(
        http_request,
        "orders",
        get_settings().order_rate_limit_per_minute,
    )
    if idempotency_key is not None:
        idempotency_key = idempotency_key.strip()
        if not idempotency_key or len(idempotency_key) > 128:
            idempotency_key = None
    order, replayed = place_customer_order(db, customer, request, idempotency_key)
    _commit(db)
    if replayed:
        response.status_code = status.HTTP_200_OK
    return order


@router.get("", response_model=PaginatedOrderResponse)
def list_my_orders(
    db: DbSession,
    customer: CurrentCustomer,
    limit: Limit = 20,
    offset: Offset = 0,
) -> PaginatedOrderResponse:
    items, total = list_customer_orders(db, customer, limit, offset)
    return PaginatedOrderResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/staff/queue", response_model=PaginatedOrderResponse)
def staff_order_queue(
    db: DbSession,
    manager: CurrentManager,
    limit: Limit = 20,
    offset: Offset = 0,
) -> PaginatedOrderResponse:
    items, total = list_managed_orders(db, manager, limit, offset)
    return PaginatedOrderResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{order_id}", response_model=OrderResponse)
def get_my_order(
    order_id: UUID,
    db: DbSession,
    customer: CurrentCustomer,
) -> OrderResponse:
    return get_customer_order(db, customer, order_id)


@router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_my_order(
    order_id: UUID,
    request: OrderCancelRequest,
    db: DbSession,
    customer: CurrentCustomer,
) -> OrderResponse:
    cancel_customer_order(db, customer, order_id, request.reason)
    _commit(db)
    return get_customer_order(db, customer, order_id)


@router.patch("/{order_id}/status", response_model=OrderResponse)
def change_order_status(
    order_id: UUID,
    request: OrderStatusUpdateRequest,
    db: DbSession,
    manager: CurrentManager,
) -> OrderResponse:
    update_order_status(
        db=db,
        user=manager,
        order_id=order_id,
        new_status=request.status,
        reason=request.reason,
    )
    _commit(db)
    return get_managed_order(db, manager, order_id)
