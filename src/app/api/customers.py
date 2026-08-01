from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.responses import success_response
from app.core.database import get_session
from app.schemas.customer import (
    CustomerCreateRequest,
    CustomerResponse,
    CustomerWithOrdersResponse,
)
from app.services.customer import CustomerService
from app.services.order import OrderService

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CustomerResponse)
async def create_customer(
    payload: CustomerCreateRequest,
    session: AsyncSession = Depends(get_session),
    _: object = Depends(get_current_user),
):
    service = CustomerService(session)
    customer = await service.create_customer(payload)
    return customer


@router.get("/{customer_id}", response_model=CustomerWithOrdersResponse)
async def get_customer(
    customer_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: object = Depends(get_current_user),
):
    service = CustomerService(session)
    customer = await service.get_customer_with_orders(customer_id)
    return customer


@router.get("/{customer_id}/orders")
async def list_customer_orders(
    customer_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _: object = Depends(get_current_user),
):
    service = OrderService(session)
    orders, total = await service.list_orders(page, page_size, customer_id=customer_id)
    return success_response(
        data=[order for order in orders],
        meta={"page": page, "page_size": page_size, "total": total, "has_next": page * page_size < total},
    )
