import enum
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, Column, Enum as SQLEnum, ForeignKey, Index, Numeric, String, func, text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class Order(BaseModel):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_uuid", "uuid"),
        Index("ix_orders_id", "id"),
        CheckConstraint("total_amount >= 0", name="ck_order_total_amount_nonnegative"),
        Index("ix_orders_customer_id", "customer_id"),
        Index("ix_orders_status", "status"),
        Index("ix_orders_created_at", "created_at"),
    )

    customer_id = Column(BigInteger, ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False)
    status = Column(
        SQLEnum(
            OrderStatus,
            name="order_status",
            native_enum=True,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        server_default=OrderStatus.PENDING.value,
    )
    total_amount = Column(Numeric(12, 2), nullable=False)
    idempotency_key = Column(String(128), nullable=False, unique=True)

    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    @property
    def customer_uuid(self) -> UUID:
        return self.customer.uuid
