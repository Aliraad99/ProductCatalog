# Product Catalog Code Review and File-by-File Explanation

## Scope Reviewed

- [src/app/main.py](src/app/main.py)
- [src/app/models](src/app/models)
- [src/app/repositories](src/app/repositories)
- [src/app/services](src/app/services)
- [src/app/api](src/app/api)
- [src/app/schemas](src/app/schemas)

## Findings (ordered by severity)

The issues below were identified during review and addressed in the code changes made alongside this report.

### 1) High: Duplicate SKU check can miss inactive products and cause DB-level conflicts

- Location: [src/app/repositories/product.py](src/app/repositories/product.py#L14), [src/app/services/product.py](src/app/services/product.py#L24), [src/app/models/product.py](src/app/models/product.py#L11)
- Why it matters:
The unique index enforces SKU uniqueness for all non-deleted products, regardless of active status. But get_by_sku with default include_deleted=false filters on both is_deleted=false and is_active=true. This means an inactive non-deleted product is invisible to the duplicate check. A create/update can then hit the DB unique index and raise an unhandled IntegrityError.
- Risk:
Unexpected 500 responses instead of clean 409 duplicate-sku responses.

### 2) High: ProductRepository.adjust_stock calls get_by_id with integer primary key but repository get_by_id expects UUID

- Location: [src/app/repositories/product.py](src/app/repositories/product.py#L37), [src/app/repositories/base.py](src/app/repositories/base.py#L19)
- Why it matters:
BaseRepository.get_by_id queries model.uuid, while adjust_stock passes product_id (int internal ID). This will almost always return None.
- Risk:
Stock adjustment helper is logically broken if used in the future.

### 3) Medium: Base model indexes on id/uuid are not inherited when subclasses override table args

- Location: [src/app/models/base.py](src/app/models/base.py#L33), [src/app/models/order.py](src/app/models/order.py#L20), [src/app/models/orderitem.py](src/app/models/orderitem.py#L10), [src/app/models/product.py](src/app/models/product.py#L8)
- Why it matters:
BaseModel defines indexes through __table_args__. Models that define their own __table_args__ replace the base tuple unless explicitly merged.
- Risk:
Missing id/uuid indexes on heavy tables can hurt query performance.

### 4) Medium: Product update endpoint is open to any authenticated user

- Location: [src/app/api/products.py](src/app/api/products.py#L63)
- Why it matters:
Create/delete routes require admin, but update uses get_current_user instead of require_admin.
- Risk:
Non-admin users can modify product catalog data.
- Note:
If this is intentional business behavior, this is not a bug. If not intentional, switch dependency to require_admin.

### 5) Low: Mutable default list in schema model

- Location: [src/app/schemas/customer.py](src/app/schemas/customer.py#L42)
- Why it matters:
orders: list[...] = [] can be surprising in Python models. Pydantic mitigates many cases, but default_factory is safer and clearer.

## File-by-File and Function-by-Function Explanation

## Main App

### [src/app/main.py](src/app/main.py)

Purpose:
Application bootstrap, router registration, global exception mapping, and health check.

Functions:

- bootstrap_admin_user:
Runs on startup. Reads ADMIN_EMAIL and ADMIN_PASSWORD from settings and creates/updates the admin account via AuthService.ensure_admin_user.

- app_http_exception_handler:
Handles custom AppHTTPException and returns standardized error payload shape.

- http_exception_handler:
Handles FastAPI/Starlette HTTPException and maps status codes to domain error codes.

- validation_exception_handler:
Handles request body/query/path validation errors and returns VALIDATION_ERROR plus detailed validation items.

- generic_exception_handler:
Fallback handler for unexpected exceptions; returns generic internal error response.

- health:
Runs SELECT 1 against DB session; returns service status when DB is reachable, else raises 503.

## Models

### [src/app/models/__init__.py](src/app/models/__init__.py)

Purpose:
Exports model classes for convenient imports and metadata discovery.

Functions:

- None.

### [src/app/models/base.py](src/app/models/base.py)

Purpose:
Defines SQLAlchemy declarative base and shared columns.

Classes and methods:

- Base:
Root SQLAlchemy declarative base.

- BaseModel:
Abstract model with shared fields id, uuid, created_at, updated_at.

- BaseModel.__table_args__:
declared_attr that builds per-table indexes on uuid and id.

### [src/app/models/customer.py](src/app/models/customer.py)

Purpose:
Customer entity with identity/contact information.

Classes and members:

- Customer:
Stores first_name, last_name, email, phone.
Defines relationship orders to Order.

Functions:

- None.

### [src/app/models/order.py](src/app/models/order.py)

Purpose:
Order aggregate root with lifecycle status and total value.

Classes and methods:

- OrderStatus:
Order state enum used in DB and business logic.

- Order:
Stores customer FK, status, total_amount, idempotency_key.
Relationships: customer and items.

- Order.customer_uuid property:
Returns related customer UUID as convenience accessor.

### [src/app/models/orderitem.py](src/app/models/orderitem.py)

Purpose:
Line item snapshot inside an order.

Classes and methods:

- OrderItem:
Stores order FK, product FK, quantity, unit_price at time of order.
Relationships: order and product.

- OrderItem.total_price property:
Computes unit_price * quantity.

### [src/app/models/product.py](src/app/models/product.py)

Purpose:
Product catalog entity with soft-delete and stock tracking.

Classes and members:

- Product:
Stores name, sku, description, unit_price, stock, is_active, is_deleted, deleted_at.
Defines unique partial index for live product SKU.
Defines relationship order_items.

Functions:

- None.

### [src/app/models/user.py](src/app/models/user.py)

Purpose:
Authentication/authorization user entity.

Classes and members:

- UserRole:
Role enum (admin, user).

- User:
Stores email, password_hash, role.

Functions:

- None.

## Repositories

### [src/app/repositories/__init__.py](src/app/repositories/__init__.py)

Purpose:
Exports repository classes and public repository API.

Functions:

- None.

### [src/app/repositories/base.py](src/app/repositories/base.py)

Purpose:
Generic async repository with shared CRUD helpers.

Methods:

- __init__:
Stores AsyncSession and model class.

- get_by_id:
Fetches one entity by UUID column.

- list_all:
Fetches all rows for the model.

- add:
Instantiates model with kwargs, adds to session, flushes.

- delete:
Deletes given entity and flushes.

### [src/app/repositories/customer.py](src/app/repositories/customer.py)

Purpose:
Customer-specific query operations.

Methods:

- __init__:
Binds repository to Customer model.

- get_by_email:
Finds customer by unique email.

- get_by_uuid:
Finds customer by UUID.

- get_with_orders:
Loads customer and preloads orders.

### [src/app/repositories/order_item.py](src/app/repositories/order_item.py)

Purpose:
Order item persistence helpers.

Methods:

- __init__:
Binds repository to OrderItem model.

- list_for_order:
Lists line items for a specific internal order ID.

### [src/app/repositories/order.py](src/app/repositories/order.py)

Purpose:
Order query operations with eager loading and filters.

Methods:

- __init__:
Binds repository to Order model.

- get_by_id_with_items:
Fetches order by UUID with customer and item->product graph loaded.

- get_by_id_with_items_for_update:
Same as above but with row-level lock for safe transactional updates.

- get_by_customer_id:
Lists orders by internal customer ID sorted newest first.

- get_by_idempotency_key:
Finds existing order by idempotency key, with related graph loaded.

- count_nonterminal_references:
Counts references from order items where order status is not delivered/cancelled.

- list_by_filters:
Paginates orders by optional status, customer UUID, and time range. Returns rows plus total count.

### [src/app/repositories/product.py](src/app/repositories/product.py)

Purpose:
Product query and stock mutation operations.

Methods:

- __init__:
Binds repository to Product model.

- get_by_sku:
Finds product by SKU, optionally including deleted/inactive behavior depending on flag.

- get_by_ids:
Fetches products by UUID list.

- decrement_stock_if_available:
Atomic stock decrement using single UPDATE with stock >= quantity guard.

- adjust_stock:
Adds delta to stock after fetching entity.

### [src/app/repositories/user.py](src/app/repositories/user.py)

Purpose:
User-specific data access.

Methods:

- __init__:
Binds repository to User model.

- get_by_email:
Finds user by email.

## Services

### [src/app/services/__init__.py](src/app/services/__init__.py)

Purpose:
Package marker for business logic layer.

Functions:

- None.

### [src/app/services/auth.py](src/app/services/auth.py)

Purpose:
Handles user registration, authentication, admin bootstrap, and token issuance.

Methods:

- __init__:
Initializes session and user repository.

- register_user:
Validates unique email, hashes password, creates user, commits, refreshes.

- authenticate_user:
Looks up user and verifies password hash.

- ensure_admin_user:
Creates admin if missing, or upgrades existing user role/password to admin credentials.

- create_access_token:
Builds JWT claims with subject and expiry.

### [src/app/services/customer.py](src/app/services/customer.py)

Purpose:
Customer business operations and domain errors.

Methods:

- __init__:
Initializes session and customer repository.

- create_customer:
Checks email uniqueness and creates customer.

- get_customer_with_orders:
Loads customer with orders or raises not found domain error.

- get_customer:
Loads customer by UUID or raises not found domain error.

### [src/app/services/order.py](src/app/services/order.py)

Purpose:
Order creation, idempotency, status transitions, cancellation, and listing.

Constants:

- VALID_TRANSITIONS:
State machine for allowed order status moves.

Methods:

- __init__:
Initializes dependent repositories.

- _normalize_items:
Aggregates duplicate product UUID rows into total quantity per product.

- _order_matches_payload:
Compares an existing order graph with incoming payload for idempotency replay safety.

- create_order:
Implements idempotency check, customer/product validation, stock decrement, order/item creation, and transaction handling.

- get_order:
Loads one order by UUID or raises not found.

- update_status:
Validates transition against state machine, updates status, commits.

- cancel_order:
Locks order row, validates cancellable states, marks cancelled, restores stock, commits.

- list_orders:
Delegates paginated filtered fetch to repository.

### [src/app/services/product.py](src/app/services/product.py)

Purpose:
Product lifecycle operations: create, list, read, update, soft delete.

Methods:

- __init__:
Initializes product and order repositories.

- create_product:
Checks for duplicate SKU among live records, inserts product, commits.

- list_products:
Returns paginated products with active/search filters and total count.

- get_product:
Loads product by UUID, rejecting deleted rows.

- update_product:
Applies partial updates and protects against SKU collision.

- soft_delete_product:
Prevents delete when product is referenced by non-terminal orders, then flags deleted/inactive.

## API Layer

### [src/app/api/__init__.py](src/app/api/__init__.py)

Purpose:
Exports all routers for app registration.

Functions:

- None.

### [src/app/api/auth.py](src/app/api/auth.py)

Purpose:
Auth endpoints for register and login.

Functions:

- register:
Accepts registration payload, calls AuthService.register_user, maps duplicate email to domain exception, returns standardized success payload.

- login:
Authenticates credentials, raises unauthorized when invalid, returns bearer token response.

### [src/app/api/customers.py](src/app/api/customers.py)

Purpose:
Customer create/read endpoints and customer-scoped order listing.

Functions:

- create_customer:
Creates a customer (authenticated).

- get_customer:
Returns customer with embedded orders (authenticated).

- list_customer_orders:
Paginates orders for one customer UUID with response metadata.

### [src/app/api/orders.py](src/app/api/orders.py)

Purpose:
Order lifecycle endpoints and serializer.

Functions:

- _serialize_order_detail:
Converts ORM order graph into explicit response dict including computed line totals.

- create_order:
Creates order using Idempotency-Key header; returns 201 on first create or 200 on replay.

- get_order:
Fetches one order by UUID.

- update_order_status:
Applies status transition.

- cancel_order:
Cancels order and performs stock restoration.

- list_orders:
Paginates and filters orders by status, customer, and date range.

### [src/app/api/products.py](src/app/api/products.py)

Purpose:
Product endpoints for CRUD-like operations.

Functions:

- create_product:
Admin-only create endpoint.

- list_products:
Authenticated list endpoint with pagination/filtering.

- get_product:
Authenticated single-product fetch.

- update_product:
Authenticated update endpoint (currently not admin-only).

- delete_product:
Admin-only soft delete endpoint.

### [src/app/api/dependencies.py](src/app/api/dependencies.py)

Purpose:
Authentication and role-based dependency functions.

Functions:

- get_current_user:
Reads bearer token, decodes JWT, loads user, raises 401 for invalid token/user.

- require_admin:
Ensures authenticated user has admin role, else raises 403.

### [src/app/api/exceptions.py](src/app/api/exceptions.py)

Purpose:
Domain HTTP exception type plus standard error code constants.

Functions:

- AppHTTPException.__init__:
Extends HTTPException with error_code and optional details payload.

### [src/app/api/responses.py](src/app/api/responses.py)

Purpose:
Unified response envelope helpers.

Functions:

- success_response:
Returns success JSON envelope with optional meta and configurable status code.

- error_response:
Returns error JSON envelope with error code, message, optional details.

### [src/app/api/product_utils.py](src/app/api/product_utils.py)

Purpose:
Pagination response helper (currently not used by routes).

Functions:

- paginated_response:
Builds standard paginated dictionary payload.

## Schemas

### [src/app/schemas/__init__.py](src/app/schemas/__init__.py)

Purpose:
Package marker for Pydantic schemas.

Functions:

- None.

### [src/app/schemas/auth.py](src/app/schemas/auth.py)

Purpose:
Request/response models for authentication.

Classes:

- UserRegisterRequest:
Validates email and password minimum length.

- UserLoginRequest:
Validates login credentials input shape.

- TokenResponse:
Token output model with access_token and token_type.

Functions:

- None.

### [src/app/schemas/customer.py](src/app/schemas/customer.py)

Purpose:
Customer request/response contracts.

Classes:

- CustomerCreateRequest:
Input model for customer creation.

- CustomerResponse:
Base customer output model mapped from ORM attributes.

- CustomerOrderItem:
Embedded order summary model used in customer-with-orders output.

- CustomerWithOrdersResponse:
Extends customer response with orders list.

Functions:

- None.

### [src/app/schemas/order.py](src/app/schemas/order.py)

Purpose:
Order API request/response contracts and status enum.

Classes:

- OrderStatus:
Allowed order statuses for API validation.

- OrderItemRequest:
Input line item with product UUID and positive quantity.

- OrderCreateRequest:
Order create payload with customer UUID and at least one item.

- OrderStatusUpdateRequest:
Payload for changing status.

- OrderItemResponse:
Output line item model with pricing totals.

- OrderListItem:
Output model for order summary/list entries.

- OrderDetailResponse:
Detailed order output model (inherits list item).

Functions:

- None.

### [src/app/schemas/pagination.py](src/app/schemas/pagination.py)

Purpose:
Reusable pagination metadata model.

Classes:

- PaginationMeta:
page, page_size, total, has_next envelope.

Functions:

- None.

### [src/app/schemas/product.py](src/app/schemas/product.py)

Purpose:
Product request/response contracts.

Classes:

- ProductCreateRequest:
Input contract for product creation.

- ProductUpdateRequest:
Partial update contract.

- ProductListItem:
List response projection mapped from ORM model.

- ProductDetailResponse:
Detailed response adding description and soft-delete fields.

Functions:

- None.
