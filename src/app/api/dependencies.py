from __future__ import annotations

from uuid import UUID

from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.exceptions import FORBIDDEN, UNAUTHORIZED, AppHTTPException
from app.core.database import get_session
from app.core.security import decode_access_token
from app.models.user import User
from app.repositories.user import UserRepository

bearer_scheme = HTTPBearer()


async def get_current_user(
    token: HTTPAuthorizationCredentials = Security(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    try:
        payload = decode_access_token(token.credentials)
        user_id = payload.get("sub")

        user_uuid = UUID(user_id)
    except (JWTError, TypeError, ValueError):
        raise AppHTTPException(
            status_code=401,
            error_code=UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = await UserRepository(session).get_by_uuid(user_uuid)
    if user is None:
        raise AppHTTPException(
            status_code=401,
            error_code=UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise AppHTTPException(
            status_code=403,
            error_code=FORBIDDEN,
            detail="Not authorized",
        )
    return current_user
