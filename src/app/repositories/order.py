from __future__ import annotations

from datetime import datetime
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.customer import Customer
from app.models.order import Order, OrderStatus
from app.models.orderitem import OrderItem
from app.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Order)

    async def get_by_id_with_items(self, order_id: UUID) -> Order | None:
        result = await self.session.execute(
            select(Order)
            .options(
                selectinload(Order.customer),
                selectinload(Order.items).selectinload(OrderItem.product),
            )
            .where(Order.uuid == order_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_items_for_update(self, order_id: UUID) -> Order | None:
        result = await self.session.execute(
            select(Order)
            .options(
                selectinload(Order.customer),
                selectinload(Order.items).selectinload(OrderItem.product),
            )
            .where(Order.uuid == order_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_by_customer_id(self, customer_id: int) -> list[Order]:
        result = await self.session.execute(
            select(Order)
            .where(Order.customer_id == customer_id)
            .order_by(Order.created_at.desc())
        )
        return result.scalars().all()

    async def get_by_idempotency_key(self, idempotency_key: str) -> Order | None:
        result = await self.session.execute(
            select(Order)
            .options(
                selectinload(Order.customer),
                selectinload(Order.items).selectinload(OrderItem.product),
            )
            .where(Order.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    async def count_nonterminal_references(self, product_id: int) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(OrderItem)
            .join(Order, OrderItem.order_id == Order.id)
            .where(
                OrderItem.product_id == product_id,
                Order.status.notin_([
                    OrderStatus.DELIVERED,
                    OrderStatus.CANCELLED,
                ]),
            )
        )
        return result.scalar_one()

    async def list_by_filters(
        self,
        page: int,
        page_size: int,
        status: OrderStatus | None = None,
        customer_id: UUID | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> tuple[list[Order], int]:
        stmt = select(Order).options(
            selectinload(Order.customer), 
            selectinload(Order.items).selectinload(OrderItem.product),
        )
        if status is not None:
            stmt = stmt.where(Order.status == status)
        if customer_id is not None:
            stmt = stmt.where(Order.customer.has(Customer.uuid == customer_id))
        if start_at is not None:
            stmt = stmt.where(Order.created_at >= start_at)
        if end_at is not None:
            stmt = stmt.where(Order.created_at <= end_at)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt)
        stmt = stmt.order_by(Order.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        return result.scalars().all(), total
