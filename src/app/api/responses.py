from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse


def success_response(
    data: dict | list | None = None,
    meta: dict | None = None,
    status_code: int = 200,
) -> JSONResponse:
    payload = {"success": True, "data": data}
    if meta is not None:
        payload["meta"] = meta
    return JSONResponse(status_code=status_code, content=jsonable_encoder(payload))


def error_response(error_code: str, message: str, details: dict | None = None, status_code: int = 400) -> JSONResponse:
    payload = {
        "success": False,
        "error": error_code,
        "message": message,
    }
    if details is not None:
        payload["details"] = details
    return JSONResponse(status_code=status_code, content=jsonable_encoder(payload))
