from __future__ import annotations
from app.api.exceptions import AppHTTPException, EMAIL_ALREADY_EXISTS, NOT_FOUND
from app.models.customer import Customer
from app.repositories.customer import CustomerRepository
from app.schemas.customer import CustomerCreateRequest
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

class CustomerService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = CustomerRepository(session)

    async def create_customer(self, payload: CustomerCreateRequest) -> Customer:
        existing = await self.repo.get_by_email(payload.email)
        if existing:
            raise AppHTTPException(
                status_code=409,
                error_code=EMAIL_ALREADY_EXISTS,
                detail="Email already exists",
            )

        customer = await self.repo.add(
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=payload.email,
            phone=payload.phone,
        )
        await self.session.commit()
        await self.session.refresh(customer)
        return customer

    async def get_customer_with_orders(self, customer_id: UUID) -> Customer:
        customer = await self.repo.get_with_orders(customer_id)
        if customer is None:
            raise AppHTTPException(
                status_code=404,
                error_code=NOT_FOUND,
                detail="Customer not found",
            )
        return customer

    async def get_customer(self, customer_id: UUID) -> Customer:
        customer = await self.repo.get_by_uuid(customer_id)
        if customer is None:
            raise AppHTTPException(
                status_code=404,
                error_code=NOT_FOUND,
                detail="Customer not found",
            )
        return customer
