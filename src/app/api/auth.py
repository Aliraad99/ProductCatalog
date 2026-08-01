from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.exceptions import EMAIL_ALREADY_EXISTS, UNAUTHORIZED, AppHTTPException
from app.api.responses import success_response
from app.core.database import get_session
from app.schemas.auth import TokenResponse, UserLoginRequest, UserRegisterRequest
from app.services.auth import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    service = AuthService(session)
    try:
        await service.register_user(payload.email, payload.password)
    except ValueError as exc:
        if str(exc) == "email_exists":
            raise AppHTTPException(
                status_code=status.HTTP_409_CONFLICT,
                error_code=EMAIL_ALREADY_EXISTS,
                detail="Email already exists",
            )
        raise

    return success_response(
        data={"message": "User created successfully"},
        status_code=status.HTTP_201_CREATED,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: UserLoginRequest,
    session: AsyncSession = Depends(get_session),
):
    service = AuthService(session)
    user = await service.authenticate_user(payload.email, payload.password)
    if user is None:
        raise AppHTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=UNAUTHORIZED,
            detail="Invalid credential",
        )

    token = service.create_access_token(user.uuid)
    return success_response(data={"access_token": token, "token_type": "bearer"})
