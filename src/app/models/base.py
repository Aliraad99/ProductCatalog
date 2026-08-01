from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import BigInteger, Column, UUID, Identity, DateTime, func
from uuid6 import uuid7

class Base(DeclarativeBase):
    pass


class BaseModel(Base):
    __abstract__ = True

    id = Column(
        BigInteger,
        Identity(),
        primary_key=True
    )

    uuid = Column(
        UUID(as_uuid=True),
        default=uuid7,
        unique=True,
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )