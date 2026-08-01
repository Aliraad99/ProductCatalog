from sqlalchemy import Column, Index, String
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Customer(BaseModel):
    __tablename__ = "customers"
    __table_args__ = (
        Index("ix_customers_uuid", "uuid"),
        Index("ix_customers_id", "id"),
    )

    first_name = Column(String(128), nullable=False)
    last_name = Column(String(128), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    phone = Column(String(32), nullable=True)

    orders = relationship("Order", back_populates="customer")
