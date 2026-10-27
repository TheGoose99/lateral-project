import hashlib
import json
from decimal import Decimal
from uuid import UUID

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.models import (
    MenuCategory,
    MenuItem,
    Order,
    OrderIdempotencyKey,
    OrderItem,
    OrderStatusHistory,
    Restaurant,
    User,
)
from app.schemas.order import OrderCreateRequest

_ORDER_LOAD_OPTIONS = (
    selectinload(Order.items),
    selectinload(Order.status_history),
    selectinload(Order.restaurant),
)


ORDER_TRANSITIONS = {
    "pending": {"accepted", "cancelled"},
    "accepted": {"preparing", "out_for_delivery", "cancelled"},
    "preparing": {"out_for_delivery", "cancelled"},
    "out_for_delivery": {"delivered"},
    "delivered": set(),
    "cancelled": set(),
}

def create_order(
    db: Session,
    customer: User,
    request: OrderCreateRequest,
) -> Order:
    restaurant = db.scalar(
        select(Restaurant).where(
            Restaurant.id == request.restaurant_id,
            Restaurant.is_active.is_(True),
        )
    )
    if restaurant is None:
        raise AppError(status.HTTP_404_NOT_FOUND, "Restaurant not found")

    requested_quantities = {item.menu_item_id: item.quantity for item in request.items}
    requested_ids = list(requested_quantities)

    menu_items = list(
        db.scalars(
            select(MenuItem)
            .join(MenuCategory, MenuItem.category_id == MenuCategory.id)
            .where(
                MenuItem.id.in_(requested_ids),
                MenuCategory.restaurant_id == restaurant.id,
            )
            .with_for_update()
        ).all()
    )

    if len(menu_items) != len(requested_ids):
        raise AppError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "One or more menu items do not belong to this restaurant",
        )

    if any(not item.is_available for item in menu_items):
        raise AppError(
            status.HTTP_409_CONFLICT,
            "One or more menu items are unavailable",
        )

    items_by_id = {item.id: item for item in menu_items}
    total = sum(
        (
            items_by_id[item_id].price * quantity
            for item_id, quantity in requested_quantities.items()
        ),
        start=Decimal("0.00"),
    ).quantize(Decimal("0.01"))

    order = Order(
        customer_id=customer.id,
        restaurant_id=restaurant.id,
        status="pending",
        total_amount=total,
        currency="RON",
    )

    for item_id, quantity in requested_quantities.items():
        menu_item = items_by_id[item_id]
        order.items.append(
            OrderItem(
                menu_item_id=menu_item.id,
                name_snapshot=menu_item.name,
                unit_price_snapshot=menu_item.price,
                quantity=quantity,
            )
        )

    order.status_history.append(
        OrderStatusHistory(
            from_status=None,
            to_status="pending",
            changed_by_user_id=customer.id,
            reason="Order placed",
        )
    )

    db.add(order)
    db.flush()
    return order


def place_customer_order(
    db: Session,
    customer: User,
    request: OrderCreateRequest,
    idempotency_key: str | None,
) -> tuple[Order, bool]:
    fingerprint = _request_fingerprint(request)
    if idempotency_key:
        existing = db.scalar(
            select(OrderIdempotencyKey).where(
                OrderIdempotencyKey.customer_id == customer.id,
                OrderIdempotencyKey.key == idempotency_key,
            )
        )
        if existing is not None:
            if existing.request_hash != fingerprint:
                raise AppError(
                    status.HTTP_409_CONFLICT,
                    "Idempotency key was already used with a different request",
                )
            return get_customer_order(db, customer, existing.order_id), True

    order = create_order(db, customer, request)
    if idempotency_key:
        db.add(
            OrderIdempotencyKey(
                customer_id=customer.id,
                key=idempotency_key,
                request_hash=fingerprint,
                order_id=order.id,
            )
        )
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            existing = db.scalar(
                select(OrderIdempotencyKey).where(
                    OrderIdempotencyKey.customer_id == customer.id,
                    OrderIdempotencyKey.key == idempotency_key,
                )
            )
            if existing is None:
                raise AppError(
                    status.HTTP_409_CONFLICT,
                    "Checkout is already being processed",
                ) from None
            if existing.request_hash != fingerprint:
                raise AppError(
                    status.HTTP_409_CONFLICT,
                    "Idempotency key was already used with a different request",
                ) from None
            return get_customer_order(db, customer, existing.order_id), True
    return get_customer_order(db, customer, order.id), False


def _request_fingerprint(request: OrderCreateRequest) -> str:
    payload = request.model_dump(mode="json")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode()).hexdigest()


def get_customer_order(
    db: Session,
    customer: User,
    order_id: UUID,
) -> Order:
    order = db.scalar(
        select(Order)
        .where(
            Order.id == order_id,
            Order.customer_id == customer.id,
        )
        .options(*_ORDER_LOAD_OPTIONS)
    )
    if order is None:
        raise AppError(status.HTTP_404_NOT_FOUND, "Order not found")
    return order


def list_customer_orders(
    db: Session,
    customer: User,
    limit: int,
    offset: int,
) -> tuple[list[Order], int]:
    filters = [Order.customer_id == customer.id]
    return _paginated_orders(db, filters, limit, offset)


def list_managed_orders(
    db: Session,
    user: User,
    limit: int,
    offset: int,
) -> tuple[list[Order], int]:
    filters = []
    if user.role == "staff":
        if user.restaurant_id is None:
            return [], 0
        filters.append(Order.restaurant_id == user.restaurant_id)

    return _paginated_orders(db, filters, limit, offset)


def get_managed_order(
    db: Session,
    user: User,
    order_id: UUID,
) -> Order:
    statement = (
        select(Order)
        .where(Order.id == order_id)
        .options(*_ORDER_LOAD_OPTIONS)
    )

    if user.role == "staff":
        if user.restaurant_id is None:
            raise AppError(status.HTTP_404_NOT_FOUND, "Order not found")
        statement = statement.where(Order.restaurant_id == user.restaurant_id)

    order = db.scalar(statement)
    if order is None:
        raise AppError(status.HTTP_404_NOT_FOUND, "Order not found")

    return order


def update_order_status(
    db: Session,
    user: User,
    order_id: UUID,
    new_status: str,
    reason: str | None = None,
) -> Order:
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())

    if order is None:
        raise AppError(status.HTTP_404_NOT_FOUND, "Order not found")

    if user.role == "staff" and (
        user.restaurant_id is None or order.restaurant_id != user.restaurant_id
    ):
        raise AppError(status.HTTP_404_NOT_FOUND, "Order not found")

    _apply_status_change(order, user, new_status, reason)
    db.flush()
    return order


def cancel_customer_order(
    db: Session,
    customer: User,
    order_id: UUID,
    reason: str,
) -> Order:
    order = db.scalar(
        select(Order)
        .where(Order.id == order_id, Order.customer_id == customer.id)
        .with_for_update()
    )
    if order is None:
        raise AppError(status.HTTP_404_NOT_FOUND, "Order not found")

    _apply_status_change(order, customer, "cancelled", reason)
    db.flush()
    return order


def _apply_status_change(
    order: Order,
    user: User,
    new_status: str,
    reason: str | None,
) -> None:
    if new_status not in ORDER_TRANSITIONS[order.status]:
        raise AppError(
            status.HTTP_409_CONFLICT,
            f"Cannot transition order from {order.status} to {new_status}",
        )

    if new_status == "cancelled" and not reason:
        raise AppError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "A reason is required to cancel an order",
        )

    previous_status = order.status
    order.status = new_status

    if new_status == "cancelled":
        order.cancellation_reason = reason

    order.status_history.append(
        OrderStatusHistory(
            from_status=previous_status,
            to_status=new_status,
            changed_by_user_id=user.id,
            reason=reason,
        )
    )


def _paginated_orders(
    db: Session,
    filters: list,
    limit: int,
    offset: int,
) -> tuple[list[Order], int]:
    count_statement = select(func.count()).select_from(Order)
    list_statement = (
        select(Order)
        .options(*_ORDER_LOAD_OPTIONS)
        .order_by(Order.created_at.desc(), Order.id.desc())
        .limit(limit)
        .offset(offset)
    )
    if filters:
        count_statement = count_statement.where(*filters)
        list_statement = list_statement.where(*filters)

    total = db.scalar(count_statement) or 0
    return list(db.scalars(list_statement).all()), total
