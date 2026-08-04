# Product Catalog Service

A production-minded FastAPI service for product, customer, and order management with PostgreSQL,
Alembic migrations, JWT authentication, and transactional stock correctness.

## Highlights

- FastAPI + async SQLAlchemy + PostgreSQL
- JWT-based authentication and role-based authorization
- Idempotent order creation via `Idempotency-Key`
- Concurrency-safe stock deduction
- Alembic-managed schema migrations
- Docker Compose setup for local development

## Tech Stack

- Python 3.13
- FastAPI
- SQLAlchemy (async)
- PostgreSQL 16
- Alembic
- Pydantic Settings

## Project Structure

```text
src/app/
	api/            # route handlers, dependencies, response helpers, exceptions
	core/           # config, security, database session
	models/         # SQLAlchemy models
	repositories/   # database access layer
	services/       # business logic layer
	schemas/        # request/response models
alembic/          # migration environment and revisions
```

## Quick Start (Docker)

### 1) Prerequisites

- Docker Desktop installed and running
- Docker Compose available (`docker compose version`)
- Ports `8000` and `5432` available

### 2) Configure environment

Create `.env` in the project root:

```bash
cp .env.example .env
```

For PowerShell on Windows:

```powershell
Copy-Item .env.example .env
```

### 3) Build and run

```bash
docker compose up --build
```

The stack starts:

- `db` (PostgreSQL)
- `app` (FastAPI)

At startup, the app container runs `alembic upgrade head` before serving traffic.

### 4) Verify health

- Health endpoint: `http://localhost:8000/health`

Expected body:

```json
{"success": true, "data": {"status": "ok"}}
```

## Environment Variables

Use `.env.example` as a template.

Required:

- `JWT_SECRET`
- `DATABASE_URL` (local non-Docker app runs)
- `DATABASE_URL_DOCKER` (Docker Compose app container)

Optional admin bootstrap:

- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`

Database container variables:

- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`

Important notes:

- In Docker Compose, the app should use host `db` (not `localhost`) for PostgreSQL.
- If your secret contains `$`, quote/escape it in `.env` to avoid interpolation issues.

## API Overview

Base URL:

- `http://localhost:8000`

OpenAPI docs:

- `http://localhost:8000/docs`

Routers:

- `/api/v1/auth`
- `/api/v1/products`
- `/api/v1/customers`
- `/api/v1/orders`

Authentication behavior:

- Public: `/api/v1/auth/*`, `/health`
- Protected: all other endpoints require Bearer JWT
- Admin-only actions: product create/update/delete

## Quick Auth Smoke Test

Register:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
	-H "Content-Type: application/json" \
	-d '{"email":"admin@example.com","password":"StrongPass123!"}'
```

Login:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
	-H "Content-Type: application/json" \
	-d '{"email":"admin@example.com","password":"StrongPass123!"}'
```

Use the returned `access_token` as `Authorization: Bearer <token>`.

## Data Integrity and Correctness

### Stock Concurrency Strategy

Stock is deducted with a conditional write:

```sql
UPDATE products
SET stock = stock - :qty
WHERE id = :id AND stock >= :qty AND is_deleted = false AND is_active = true
```

This prevents overselling under concurrent requests without read-modify-write races.

### Invariants

- `stock >= 0`
- `unit_price >= 0`
- `quantity > 0`
- `total_amount >= 0`
- unique email constraints for users/customers
- unique order `idempotency_key`

### Idempotency

- Same key + same payload: returns existing order
- Same key + different payload: conflict

## Pagination

Offset pagination is used with:

- `page`
- `page_size` (max 100)
- `total`
- `has_next`

## Operational Notes

- Password hashing uses Argon2.
- Database pool sizing is configurable (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`).
- Admin bootstrap runs on startup only when both `ADMIN_EMAIL` and `ADMIN_PASSWORD` are set.

## Known Gaps

- Unit/integration test suite is not yet implemented.

## Additional Design Notes

Detailed architecture and review rationale are documented in:

- `CODE_REVIEW_AND_EXPLANATIONS.md`

