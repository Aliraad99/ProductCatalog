from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.core.config import settings
from app.models.user import User, UserRole
from app.repositories.user import UserRepository
from sqlalchemy.ext.asyncio import AsyncSession


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)

    async def register_user(self, email: str, password: str) -> User:
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise ValueError("email_exists")

        password_hash = hash_password(password)
        user = await self.user_repo.add(email=email, password_hash=password_hash)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def authenticate_user(self, email: str, password: str) -> User | None:
        user = await self.user_repo.get_by_email(email)
        if user is None:
            return None

        if not verify_password(user.password_hash, password):
            return None

        return user

    async def ensure_admin_user(self, email: str, password: str) -> User:
        existing = await self.user_repo.get_by_email(email)
        password_hash = hash_password(password)

        if existing is None:
            user = await self.user_repo.add(
                email=email,
                password_hash=password_hash,
                role=UserRole.ADMIN.value,
            )
            await self.session.commit()
            await self.session.refresh(user)
            return user

        needs_update = False
        if existing.role != UserRole.ADMIN.value:
            existing.role = UserRole.ADMIN.value
            needs_update = True

        if not verify_password(existing.password_hash, password):
            existing.password_hash = password_hash
            needs_update = True

        if needs_update:
            await self.session.commit()
            await self.session.refresh(existing)

        return existing

    def create_access_token(self, user_id: UUID) -> str:
        payload = {
            "sub": str(user_id),
            "exp": datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        }
        return create_access_token(payload)
