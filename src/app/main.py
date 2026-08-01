import logging

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.api import auth, customers, orders, products
from app.api.exceptions import (
    FORBIDDEN,
    INTERNAL_ERROR,
    NOT_FOUND,
    UNAUTHORIZED,
    VALIDATION_ERROR,
    AppHTTPException,
)
from app.api.responses import error_response
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.database import get_session
from app.services.auth import AuthService

logger = logging.getLogger(__name__)

app = FastAPI(title="Product Catalog - Order Service")

app.include_router(auth)
app.include_router(products)
app.include_router(customers)
app.include_router(orders)


@app.on_event("startup")
async def bootstrap_admin_user() -> None:
    admin_email = (settings.ADMIN_EMAIL or "").strip()
    admin_password = (settings.ADMIN_PASSWORD or "").strip()

    if not admin_email or not admin_password:
        logger.info("Admin bootstrap skipped: ADMIN_EMAIL or ADMIN_PASSWORD not set")
        return

    async with AsyncSessionLocal() as session:
        service = AuthService(session)
        await service.ensure_admin_user(admin_email, admin_password)
        logger.info("Admin bootstrap completed for %s", admin_email)

@app.exception_handler(AppHTTPException)
async def app_http_exception_handler(request: Request, exc: AppHTTPException) -> JSONResponse:
    return error_response(
        error_code=exc.error_code,
        message=str(exc.detail),
        details=getattr(exc, "details", None),
        status_code=exc.status_code,
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    status_to_code = {
        status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN: FORBIDDEN,
        status.HTTP_404_NOT_FOUND: NOT_FOUND,
    }
    error_code = status_to_code.get(exc.status_code, INTERNAL_ERROR)
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    details = None if isinstance(exc.detail, str) else {"detail": exc.detail}
    return error_response(
        error_code=error_code,
        message=message,
        details=details,
        status_code=exc.status_code,
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response(
        error_code=VALIDATION_ERROR,
        message="Validation failed",
        details={"errors": exc.errors()},
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return error_response(
        error_code=INTERNAL_ERROR,
        message="Internal server error",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

@app.get("/health")
async def health(session: AsyncSession = Depends(get_session)):
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unreachable",
        )
    return {"success": True, "data": {"status": "ok"}}