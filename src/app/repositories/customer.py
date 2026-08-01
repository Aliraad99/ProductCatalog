from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from uuid import UUID

from app.models.customer import Customer
from app.repositories.base import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Customer)

    async def get_by_email(self, email: str) -> Customer | None:
        result = await self.session.execute(
            select(Customer).where(Customer.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_by_uuid(self, customer_id: UUID) -> Customer | None:
        result = await self.session.execute(
            select(Customer).where(Customer.uuid == customer_id)
        )
        return result.scalar_one_or_none()

    async def get_with_orders(self, customer_id: UUID) -> Customer | None:
        result = await self.session.execute(
            select(Customer)
            .options(selectinload(Customer.orders))
            .where(Customer.uuid == customer_id)
        )
        return result.scalar_one_or_none()
