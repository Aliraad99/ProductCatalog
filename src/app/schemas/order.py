from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID
from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class OrderItemRequest(BaseModel):
    product_id: UUID
    quantity: int = Field(..., gt=0)


class OrderCreateRequest(BaseModel):
    customer_id: UUID
    items: list[OrderItemRequest] = Field(..., min_length=1)


class OrderStatusUpdateRequest(BaseModel):
    status: OrderStatus


class OrderItemResponse(BaseModel):
    product_id: UUID
    quantity: int
    unit_price: Decimal
    total_price: Decimal

    model_config = {"from_attributes": True}


class OrderListItem(BaseModel):
    id: int
    uuid: UUID
    customer_uuid: UUID
    status: OrderStatus
    total_amount: Decimal
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse]
    
    model_config = {"from_attributes": True}


class OrderDetailResponse(OrderListItem):
    items: list[OrderItemResponse]

    model_config = {"from_attributes": True}
