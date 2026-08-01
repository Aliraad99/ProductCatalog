# Project Start Guide

## 1) Prerequisites

- Docker Desktop installed and running
- Docker Compose available (`docker compose version`)
- Ports `8000` and `5432` are free

## 2) Prepare environment file

Create `.env` in the project root.

You can copy from `.env.example`, then update values as needed.

Important: if your `JWT_SECRET` contains `$`, escape each `$` as `$$` to avoid Docker Compose interpolation warnings.


## 3) Build and start services

Run from the project root:

```bash
docker compose up --build
```

This starts:

- `db` (PostgreSQL 16)
- `app` (FastAPI)

The app container runs Alembic migrations automatically before starting the API.
Admin user will be created

## 4) Verify application is up

Open:

- http://localhost:8000/health

Expected response includes `"status": "ok"`.

## 5) Quick auth smoke test

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

Use returned `access_token` as Bearer token for protected routes.


