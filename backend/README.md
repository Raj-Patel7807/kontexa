# Kontexa Backend

The backend is a Python 3.12+ FastAPI modular monolith. Its currently exposed routes are
readiness checks at `GET /health` and `GET /api/v1/health`; both probe PostgreSQL and Redis.

## Run locally

Configure `backend/.env` with a `DATABASE_URL` before starting the application. The example file
includes a local connection string as a comment.

```bash
uv sync
uv run uvicorn kontexa.main:app --reload --port 8000
```

Run from the `backend/` directory. For the complete environment setup, see
[docs/development/setup.md](../docs/development/setup.md).

## Database changes

Alembic migrations in `migrations/` are the application schema source of truth. Apply them to a
configured database with:

```bash
uv run alembic upgrade head
```

`../infrastructure/database/schema.sql` is an equivalent bootstrap script intended only for a new,
empty Aiven PostgreSQL service. Do not use it to update an existing application database.

## Verification

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```
