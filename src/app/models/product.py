from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Index, Integer, Numeric, String, text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Product(BaseModel):
    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_uuid", "uuid"),
        Index("ix_products_id", "id"),
        CheckConstraint("stock >= 0", name="ck_product_stock_nonnegative"),
        CheckConstraint("unit_price >= 0", name="ck_product_unit_price_nonnegative"),
        Index(
            "uq_products_sku_active",
            "sku",
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND is_deleted = false"),
        ),
        Index("ix_products_active", "is_active", "deleted_at"),
    )

    name = Column(String(255), nullable=False)
    sku = Column(String(64), nullable=False)
    description = Column(String(1024), nullable=True)
    unit_price = Column(Numeric(12, 2), nullable=False)
    stock = Column(Integer, nullable=False, server_default=text("0"))
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    order_items = relationship("OrderItem", back_populates="product")
