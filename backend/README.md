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
