from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.exceptions import PRODUCT_REFERENCED, AppHTTPException, DUPLICATE_SKU, NOT_FOUND
from app.models.product import Product
from app.repositories.order import OrderRepository
from app.repositories.product import ProductRepository
from app.schemas.product import ProductCreateRequest, ProductUpdateRequest


class ProductService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ProductRepository(session)
        self.order_repo = OrderRepository(session)

    async def create_product(self, payload: ProductCreateRequest) -> Product:
        existing = await self.repo.get_by_sku(payload.sku)
        if existing:
            raise AppHTTPException(
                status_code=409,
                error_code=DUPLICATE_SKU,
                detail="Duplicate SKU among live products",
            )

        product = await self.repo.add(
            name=payload.name,
            sku=payload.sku,
            description=payload.description,
            unit_price=payload.unit_price,
            stock=payload.stock,
            is_active=payload.is_active,
        )
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def list_products(
        self,
        page: int,
        page_size: int,
        active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> tuple[list[Product], int]:
        stmt = select(Product).where(Product.is_deleted == False)
        if active is not None:
            stmt = stmt.where(Product.is_active == active)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                Product.name.ilike(pattern) | Product.sku.ilike(pattern)
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt)

        stmt = stmt.order_by(Product.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        return result.scalars().all(), total

    async def get_product(self, product_id: UUID) -> Product:
        product = await self.repo.get_by_uuid(product_id)
        if product is None or product.is_deleted:
            raise AppHTTPException(
                status_code=404,
                error_code=NOT_FOUND,
                detail="Product not found",
            )
        return product

    async def update_product(self, product_id: UUID, payload: ProductUpdateRequest) -> Product:
        product = await self.get_product(product_id)
        if payload.sku and payload.sku != product.sku:
            collision = await self.repo.get_by_sku(payload.sku)
            if collision and collision.id != product.id:
                raise AppHTTPException(
                    status_code=409,
                    error_code=DUPLICATE_SKU,
                    detail="Duplicate SKU among live products",
                )

        if payload.name is not None:
            product.name = payload.name
        if payload.sku is not None:
            product.sku = payload.sku
        if payload.description is not None:
            product.description = payload.description
        if payload.unit_price is not None:
            product.unit_price = payload.unit_price
        if payload.stock is not None:
            product.stock = payload.stock
        if payload.is_active is not None:
            product.is_active = payload.is_active

        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def soft_delete_product(self, product_id: UUID) -> None:
        product = await self.get_product(product_id)
        blocked = await self.order_repo.count_nonterminal_references(product.id)
        if blocked > 0:
            raise AppHTTPException(
                status_code=409,
                error_code=PRODUCT_REFERENCED,
                detail="Product is referenced by non-terminal orders",
            )

        product.is_deleted = True
        product.deleted_at = datetime.utcnow()
        product.is_active = False
        await self.session.commit()
