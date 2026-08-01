import enum
from sqlalchemy import Column, Enum as SQLEnum, Index, String
from app.models.base import BaseModel


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


class User(BaseModel):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_uuid", "uuid"),
        Index("ix_users_id", "id"),
    )

    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)

    role = Column(
        SQLEnum(
            UserRole,
            name="user_role",
            native_enum=True,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        server_default=UserRole.USER.value,
    )
