from .auth import router as auth
from .products import router as products
from .customers import router as customers
from .orders import router as orders

__all__ = ["auth", "products", "customers", "orders"]
