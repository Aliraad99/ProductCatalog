#                   Product Catalog



### Project Structure

```text
src/app/
	api/            # route handlers, dependencies, response helpers, error
	core/           # config, security, database session
	models/         # SQLAlchemy ORMM odels
	repositories/   # DB access layer
	services/       # business logic layer
	schemas/        # request/response Pydantic schemas
alembic/          # migration environment and revisions
tests/            # not implemented
```

##  Setup and Run: Docker Compose (App + PostgreSQL)

From a clean machine run:

docker compose up --build


### Authentication

- All endpoints except `/api/v1/auth/*` and `/health` require Bearer JWT.
- Role claim is used for admin-only operations (for example product creation/deletion).

### Primary Key Strategy

- Internal relational key: `BIGINT IDENTITY` (`id`) for join performance.
- External/API key: UUID (`uuid`) using UUIDv7 generation for better index locality than random UUIDv4.

### Constraints and Invariants

Invariants enforced in DB and application layer:

- `CHECK (stock >= 0)` on products
- `CHECK (unit_price >= 0)` on products and order items
- `CHECK (quantity > 0)` on order items
- `CHECK (total_amount >= 0)` on orders

- Unique customer email, user email, and idempotency key

### Soft Delete and SKU Uniqueness

- Products are soft-deleted (`is_deleted`, `deleted_at`).
- Partial unique index enforces SKU uniqueness only among live rows:
	`uq_products_sku_active` with predicate `deleted_at IS NULL AND is_deleted = false`.

### Order Status Representation

- Stored as a native PostgreSQL enum (`order_status`).

### Indexes and Rationale

- `ix_*_id`, `ix_*_uuid`: fast primary/external lookups.
- `uq_products_sku_active`: protects live SKU uniqueness.
- `ix_products_active`: accelerates active product filtering.
- `ix_orders_customer_id`: customer order listing.
- `ix_orders_status`: status filtering.
- `ix_orders_created_at`: recent-first queries and date range filtering.
- `ix_order_items_order_id`, `ix_order_items_product_id`: join/query efficiency for order details and references.

### N+1 Avoidance

- `selectinload` is used for loading order-with-items and customer-with-orders paths in repository methods.

## Concurrency and Correctness Strategy

### Chosen Strategy

Conditional write for stock deduction:

```sql
UPDATE products
SET stock = stock - :qty
WHERE id = :id AND stock >= :qty AND is_deleted = false AND is_active = true
```

The operation succeeds only if exactly one row is affected.

### Why This Works

- Prevents overselling without read-modify-write race.
- Keeps stock transitions atomic at row level.
- Works well with PostgreSQL MVCC and row-level locking behavior during update.

### Deadlock Ordering

- When creating orders with multiple products, product IDs are processed in sorted order.
- Deterministic ordering reduces cyclic lock acquisition risk.

### Idempotency Behavior

- `idempotency_key` has a DB unique constraint.
- Same key + same payload returns previous order.
- Same key + different payload returns conflict (`IDEMPOTENCY_KEY_CONFLICT`).

Retention note:

- Current implementation retains keys indefinitely because they are stored on the `orders` table.
- A production variant could add TTL archival/purge policy.

### Cancellation Exactly Once

- Cancellation fetches order using `SELECT ... FOR UPDATE` and applies stock restore only if status is cancellable.
- Concurrent cancellation attempts serialize; once status changes to `CANCELLED`, subsequent attempts fail by state rule.

## Pagination Choice

Chosen approach: offset pagination (`page`, `page_size`, `total`, `has_next`).

Reasoning:

- Simpler API contract for task scope and reviewer validation.
- Easy to combine with filters.
- Capped `page_size` (max 100) controls query cost.

Trade-off:

- Offset cost grows with deeper pages; keyset pagination is better for very large scans.

##  Non-Functional Notes

- Password hashing uses Argon2.
- DB pool sizing is explicit in settings (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`).
- Migrations are run via Alembic and Docker startup path applies migrations before serving.
- Sensitive payloads (tokens/passwords/full credential bodies) will never be logged.



##  What Is Deliberately Not Finished Yet

test unit

## 14. Written Answers

### ) Which concurrency strategy did you choose for stock deduction, and what happens to it at fifty times the load?

I chose conditional writes (`UPDATE ... WHERE stock >= :qty`) for stock deduction. 
This avoids the classic race in read-then-write logic and keeps correctness in the database where contention.

### ) GET /api/v1/products needs to serve 10,000 requests per second. What breaks first, and what do you change?

The first break is usually database pressure from repeated filtered reads and offset scans,
followed by connection pool saturation and serialization overhead in the API layer. I would
introduce a read-through cache for hot product lists/search terms, move deep pagination paths
to keyset pagination for better asymptotic performance. At the app tier, I would profile JSON
serialization and tune worker/process counts to match CPU and network behavior.

### ) Which of your indexes would you drop first if write throughput became the bottleneck, and how would you decide?

I would start by measuring index utility via `pg_stat_user_indexes` and query plans, then drop
the least-used non-critical index first. In this schema, likely candidates are broad helper indexes
that are not tied to strict constraints, such as an activity composite if query evidence is weak.
I would never drop integrity-critical indexes (for example partial unique SKU) without an
alternative guarantee. The decision is evidence-driven: low scan usage, high write amplification,
and no regression in representative production queries after controlled rollout.

### ) What did you deliberately not build, and what would you do differently with a full week?

I prioritized core consistency, data integrity, and transactional behavior over optional breadth.
With a full week, I would add observability dashboards, and migration safety checks in CI. I would also
add load-focused profiling and tune read/write paths based on measured bottlenecks rather than
assumptions.

