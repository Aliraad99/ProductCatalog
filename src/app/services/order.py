from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.exceptions import (
    AppHTTPException,
    IDEMPOTENCY_KEY_CONFLICT,
    INSUFFICIENT_STOCK,
    NOT_FOUND,
    PRODUCT_INACTIVE,
    INVALID_STATUS_TRANSITION,
    CANCELLATION_NOT_ALLOWED,
)
from app.models.order import Order, OrderStatus
from app.models.product import Product
from app.repositories.customer import CustomerRepository
from app.repositories.order import OrderRepository
from app.repositories.order_item import OrderItemRepository
from app.repositories.product import ProductRepository
from app.schemas.order import OrderCreateRequest, OrderItemRequest, OrderStatusUpdateRequest


VALID_TRANSITIONS = {
    OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.PROCESSING, OrderStatus.CANCELLED},
    OrderStatus.PROCESSING: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}


class OrderService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.customer_repo = CustomerRepository(session)
        self.product_repo = ProductRepository(session)
        self.order_repo = OrderRepository(session)
        self.order_item_repo = OrderItemRepository(session)

    @staticmethod
    def _normalize_items(items: list[OrderItemRequest]) -> dict[UUID, int]:
        quantities: dict[UUID, int] = defaultdict(int)
        for item in items:
            quantities[item.product_id] += item.quantity
        return quantities

    @staticmethod
    def _order_matches_payload(order: Order, payload: OrderCreateRequest) -> bool:
        if order.customer.uuid != payload.customer_id:
            return False

        payload_quantities: dict[UUID, int] = defaultdict(int)
        for item in payload.items:
            payload_quantities[item.product_id] += item.quantity

        order_quantities: dict[UUID, int] = defaultdict(int)
        for item in order.items:
            order_quantities[item.product.uuid] += item.quantity

        return payload_quantities == order_quantities

    async def create_order(self, payload: OrderCreateRequest, idempotency_key: str) -> tuple[Order, bool]:
        existing = await self.order_repo.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            if self._order_matches_payload(existing, payload):
                return existing, True
            raise AppHTTPException(
                status_code=409,
                error_code=IDEMPOTENCY_KEY_CONFLICT,
                detail="Idempotency key reused with a different order payload",
            )

        customer = await self.customer_repo.get_by_uuid(payload.customer_id)
        if customer is None:
            raise AppHTTPException(
                status_code=404,
                error_code=NOT_FOUND,
                detail="Customer not found",
            )

        requested_quantities = self._normalize_items(payload.items)
        requested_product_uuids = sorted(requested_quantities.keys())
        products = await self.product_repo.get_by_ids(requested_product_uuids)
        products_by_uuid = {product.uuid: product for product in products}

        missing_uuids = [product_uuid for product_uuid in requested_product_uuids if product_uuid not in products_by_uuid]
        if missing_uuids:
            raise AppHTTPException(
                status_code=404,
                error_code=NOT_FOUND,
                detail="Products not found",
                details={"missing_product_uuids": missing_uuids},
            )

        total_amount = Decimal(0)
        for product_uuid, quantity in requested_quantities.items():
            product = products_by_uuid[product_uuid]
            if product.is_deleted or not product.is_active:
                raise AppHTTPException(
                    status_code=409,
                    error_code=PRODUCT_INACTIVE,
                    detail="Inactive or deleted product referenced",
                    details={"product_uuid": product_uuid},
                )
            total_amount += product.unit_price * quantity

        order = await self.order_repo.add(
            customer_id=customer.id,
            total_amount=total_amount,
            idempotency_key=idempotency_key,
        )

        try:
            for product_uuid in requested_product_uuids:
                product = products_by_uuid[product_uuid]
                quantity = requested_quantities[product_uuid]
                success = await self.product_repo.decrement_stock_if_available(product.id, quantity)
                if not success:
                    raise AppHTTPException(
                        status_code=409,
                        error_code=INSUFFICIENT_STOCK,
                        detail="Insufficient stock for one or more products",
                        details={"product_uuid": product_uuid},
                    )

            for item in payload.items:
                product = products_by_uuid[item.product_id]
                await self.order_item_repo.add(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=item.quantity,
                    unit_price=product.unit_price,
                )

            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            existing = await self.order_repo.get_by_idempotency_key(idempotency_key)
            if existing is not None:
                if existing and self._order_matches_payload(existing, payload):
                    return existing, True
                raise AppHTTPException(
                    status_code=409,
                    error_code=IDEMPOTENCY_KEY_CONFLICT,
                    detail="Idempotency key reused with a different order payload",
                )
            raise

        saved_order = await self.order_repo.get_by_id_with_items(order.uuid)
        return saved_order or order, False

    async def get_order(self, order_id: UUID) -> Order:
        order = await self.order_repo.get_by_id_with_items(order_id)
        if order is None:
            raise AppHTTPException(
                status_code=404,
                error_code=NOT_FOUND,
                detail="Order not found",
            )
        return order

    async def update_status(self, order_id: UUID, payload: OrderStatusUpdateRequest) -> Order:
        order = await self.order_repo.get_by_id_with_items(order_id)
        if order is None:
            raise AppHTTPException(
                status_code=404,
                error_code=NOT_FOUND,
                detail="Order not found",
            )

        if payload.status not in VALID_TRANSITIONS[order.status]:
            raise AppHTTPException(
                status_code=409,
                error_code=INVALID_STATUS_TRANSITION,
                detail=f"Invalid status transition from {order.status} to {payload.status}",
            )

        previous_status = order.status
        order.status = payload.status
        await self.session.commit()
        order.previous_status = previous_status
        updated_order = await self.order_repo.get_by_id_with_items(order_id)
        return updated_order or order

    async def cancel_order(self, order_id: UUID) -> Order:
        order = await self.order_repo.get_by_id_with_items_for_update(order_id)
        if order is None:
            raise AppHTTPException(
                status_code=404,
                error_code=NOT_FOUND,
                detail="Order not found",
            )

        if order.status not in {OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PROCESSING}:
            raise AppHTTPException(
                status_code=409,
                error_code=CANCELLATION_NOT_ALLOWED,
                detail="Cancellation not allowed for the current status",
            )

        order.status = OrderStatus.CANCELLED
        product_uuids = sorted({item.product.uuid for item in order.items})
        products = await self.product_repo.get_by_ids(product_uuids)
        products_by_id = {product.id: product for product in products}

        for item in order.items:
            product = products_by_id.get(item.product_id)
            if product is not None:
                product.stock += item.quantity

        await self.session.commit()
        cancelled_order = await self.order_repo.get_by_id_with_items(order_id)
        return cancelled_order or order

    async def list_orders(
        self,
        page: int,
        page_size: int,
        status: OrderStatus | None = None,
        customer_id: UUID | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> tuple[list[Order], int]:
        return await self.order_repo.list_by_filters(
            page=page,
            page_size=page_size,
            status=status,
            customer_id=customer_id,
            start_at=start_at,
            end_at=end_at,
        )
