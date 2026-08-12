# Kontexa Backend

FastAPI Python backend for Kontexa modular monolith architecture.

## Usage

```bash
# Sync environment dependencies
uv sync

# Run backend development server
uv run uvicorn kontexa.main:app --reload --port 8000

# Run tests
uv run pytest
```

## Database schema

Apply schema changes through Alembic:

```bash
uv run alembic upgrade head
```

For a newly provisioned Aiven PostgreSQL service, a standalone equivalent schema is available at
[`../infrastructure/database/schema.sql`](../infrastructure/database/schema.sql). Configure the
service's CA certificate with `DATABASE_CA_CERT` before connecting the application. The SQL schema
creates the `pgcrypto`, `uuid-ossp`, and `vector` extensions; confirm that the Aiven service user
has permission to enable extensions before running it.

## Readiness endpoint

`GET /health` verifies the PostgreSQL and Redis connections used by the application. The response
includes the service version, environment, check timestamp, and per-dependency latency. It returns
HTTP 200 when all required dependencies are available, otherwise HTTP 503 with a degraded status.
