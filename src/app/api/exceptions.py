from fastapi import HTTPException
from starlette import status


class AppHTTPException(HTTPException):
    def __init__(
        self,
        status_code: int,
        error_code: str,
        detail: str,
        headers: dict | None = None,
        details: dict | None = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code
        self.details = details or {}


VALIDATION_ERROR = "VALIDATION_ERROR"
UNAUTHORIZED = "UNAUTHORIZED"
FORBIDDEN = "FORBIDDEN"
NOT_FOUND = "NOT_FOUND"
EMAIL_ALREADY_EXISTS = "EMAIL_ALREADY_EXISTS"
DUPLICATE_SKU = "DUPLICATE_SKU"
PRODUCT_INACTIVE = "PRODUCT_INACTIVE"
INSUFFICIENT_STOCK = "INSUFFICIENT_STOCK"
INVALID_STATUS_TRANSITION = "INVALID_STATUS_TRANSITION"
CANCELLATION_NOT_ALLOWED = "CANCELLATION_NOT_ALLOWED"
IDEMPOTENCY_KEY_CONFLICT = "IDEMPOTENCY_KEY_CONFLICT"
PRODUCT_REFERENCED = "PRODUCT_REFERENCED"
INTERNAL_ERROR = "INTERNAL_ERROR"
