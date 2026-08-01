from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.responses import success_response
from app.core.database import get_session
from app.schemas.order import (
    OrderCreateRequest,
    OrderStatus,
    OrderStatusUpdateRequest,
)
from app.services.order import OrderService

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


def _serialize_order_detail(order) -> dict:
    return {
        "id": order.id,
        "uuid": order.uuid,
        "customer_uuid": order.customer.uuid,
        "status": order.status,
        "total_amount": order.total_amount,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "items": [
            {
                "product_id": item.product.uuid,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total_price": item.total_price,
            }
            for item in order.items
        ],
    }
@router.post("", status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreateRequest,
    x_idempotency_key: str = Header(..., alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_session),
    _: object = Depends(get_current_user),
):
    service = OrderService(session)
    order, replayed = await service.create_order(payload, x_idempotency_key)
    response_status = status.HTTP_200_OK if replayed else status.HTTP_201_CREATED
    return success_response(data=_serialize_order_detail(order), status_code=response_status)


@router.get("/{order_id}")
async def get_order(
    order_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: object = Depends(get_current_user),
):
    service = OrderService(session)
    order = await service.get_order(order_id)
    return success_response(data=_serialize_order_detail(order))


@router.patch("/{order_id}/status")
async def update_order_status(
    order_id: UUID,
    payload: OrderStatusUpdateRequest,
    session: AsyncSession = Depends(get_session),
    _: object = Depends(get_current_user),
):
    service = OrderService(session)
    order = await service.update_status(order_id, payload)
    return success_response(data=_serialize_order_detail(order))


@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: object = Depends(get_current_user),
):
    service = OrderService(session)
    order = await service.cancel_order(order_id)
    return success_response(data=_serialize_order_detail(order))


@router.get("")
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: OrderStatus | None = Query(None),
    customer_id: UUID | None = Query(None),
    start_at: datetime | None = Query(None),
    end_at: datetime | None = Query(None),
    session: AsyncSession = Depends(get_session),
    _: object = Depends(get_current_user),
):
    status_filter = status
    service = OrderService(session)
    orders, total = await service.list_orders(page, page_size, status_filter, customer_id, start_at, end_at)
    return success_response(
        data=[_serialize_order_detail(order) for order in orders],
        meta={"page": page, "page_size": page_size, "total": total, "has_next": page * page_size < total},
    )
