from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from uuid import UUID


class ProductCreateRequest(BaseModel):

    
    name: str = Field(..., max_length=255)
    sku: str = Field(..., max_length=64)
    description: str | None = Field(default=None, max_length=1024)
    unit_price: Decimal = Field(..., ge=0)
    stock: int = Field(default=0, ge=0)
    is_active: bool = True


class ProductUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    sku: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=1024)
    unit_price: Decimal | None = Field(default=None, ge=0)
    stock: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class ProductListItem(BaseModel):
    id: int
    uuid: UUID
    name: str
    sku: str
    unit_price: Decimal
    stock: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductDetailResponse(ProductListItem):
    description: str | None
    is_deleted: bool
    deleted_at: datetime | None
