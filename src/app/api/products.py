from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_admin
from app.api.responses import success_response
from app.core.database import get_session
from app.schemas.product import (
    ProductCreateRequest,
    ProductDetailResponse,
    ProductListItem,
    ProductUpdateRequest,
)
from app.services.product import ProductService

router = APIRouter(prefix="/api/v1/products", tags=["products"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreateRequest,
    session: AsyncSession = Depends(get_session),
    _: object = Depends(require_admin),
):
    service = ProductService(session)
    product = await service.create_product(payload)
    return success_response(
        data=ProductDetailResponse.from_orm(product).model_dump(mode="json"),
        status_code=status.HTTP_201_CREATED,
    )


@router.get("")
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    active: bool | None = Query(None),
    search: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
    _: object = Depends(get_current_user),
):
    service = ProductService(session)
    products, total = await service.list_products(page, page_size, active, search)
    return success_response(
        data=[ProductListItem.from_orm(product).model_dump(mode="json") for product in products],
        meta={"page": page, "page_size": page_size, "total": total, "has_next": page * page_size < total},
    )


@router.get("/{product_id}")
async def get_product(
    product_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: object = Depends(get_current_user),
):
    service = ProductService(session)
    product = await service.get_product(product_id)
    return success_response(data=ProductDetailResponse.from_orm(product).model_dump(mode="json"))


@router.patch("/{product_id}")
async def update_product(
    product_id: UUID,
    payload: ProductUpdateRequest,
    session: AsyncSession = Depends(get_session),
    _: object = Depends(require_admin),
):
    service = ProductService(session)
    product = await service.update_product(product_id, payload)
    return success_response(data=ProductDetailResponse.from_orm(product).model_dump(mode="json"))


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: object = Depends(require_admin),
):
    service = ProductService(session)
    await service.soft_delete_product(product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
