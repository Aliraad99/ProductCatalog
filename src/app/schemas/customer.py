from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID


class CustomerCreateRequest(BaseModel):
    first_name: str = Field(..., max_length=128)
    last_name: str = Field(..., max_length=128)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=32)


class CustomerResponse(BaseModel):
    id: int
    uuid: UUID
    first_name: str
    last_name: str
    email: EmailStr
    phone: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CustomerOrderItem(BaseModel):
    id: int
    uuid: UUID
    customer_id: int
    status: str
    total_amount: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CustomerWithOrdersResponse(CustomerResponse):
    orders: list[CustomerOrderItem] = []
