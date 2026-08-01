from __future__ import annotations
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.repositories.base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Product)

    async def get_by_sku(self, sku: str, include_deleted: bool = False) -> Product | None:
        stmt = select(Product).where(Product.sku == sku)
        if not include_deleted:
            stmt = stmt.where(Product.is_deleted == False)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_ids(self, product_uuids: list[UUID]) -> list[Product]:
        result = await self.session.execute(select(Product).where(Product.uuid.in_(product_uuids)))
        return result.scalars().all()

    async def decrement_stock_if_available(self, product_id: int, quantity: int) -> bool:
        result = await self.session.execute(
            update(Product)
            .where(
                Product.id == product_id,
                Product.stock >= quantity,
                Product.is_deleted == False,
                Product.is_active == True,
            )
            .values(stock=Product.stock - quantity)
        )
        return result.rowcount == 1

    async def adjust_stock(self, product_id: int, delta: int) -> Product | None:
        product = await self.get_by_pk(product_id)
        if product is None:
            return None
        product.stock += delta
        await self.session.flush()
        return product
