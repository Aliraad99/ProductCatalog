from __future__ import annotations

from app.api.responses import success_response
from app.schemas.pagination import PaginationMeta


def paginated_response(data: list, page: int, page_size: int, total: int) -> dict:
    return {
        "success": True,
        "data": data,
        "meta": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "has_next": (page * page_size) < total,
        },
    }
