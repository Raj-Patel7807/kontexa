# Local Development Setup

## Prerequisites

- Python 3.12 or newer and `uv`
- Node.js 20 or newer and npm
- Docker with Docker Compose
- GNU Make or a compatible `make` implementation

## Configure local environment files

Copy the example files if you want local overrides:

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Before running the backend locally, add or uncomment `DATABASE_URL` in `backend/.env`. The backend
loads `.env` from the `backend/` working directory, so the root `.env` alone is insufficient for
`make dev`. The default local URL is documented in the commented example line. `REDIS_URL` defaults
to `redis://localhost:6379/0` if not supplied.

For every supported variable and its runtime behavior, see [../CONFIGURATION.md](../CONFIGURATION.md).

## Install dependencies

```bash
make setup
```

This runs `uv sync` in `backend/` and `npm install` in `frontend/`. The individual equivalents are:

```bash
cd backend && uv sync
cd frontend && npm install
```

## Run the full containerized stack

```bash
make up
```

This runs `docker compose -f infrastructure/docker/docker-compose.yml up -d` and starts
PostgreSQL, Redis, backend, and frontend. The services are available at ports 5432, 6379, 8000, and
3000 respectively. Check them with:

```bash
docker compose -f infrastructure/docker/docker-compose.yml ps
```

Stop the stack with `make down`.

## Run frontend and backend locally

Start the services in separate terminals after PostgreSQL and Redis are available:

```bash
cd backend && uv run uvicorn kontexa.main:app --reload --port 8000
```

```bash
cd frontend && npm run dev
```

`make dev` starts those same commands together. The local frontend defaults to a rewrite target of
`http://localhost:8000`. Visit `http://localhost:3000` to see the status dashboard; it polls
`/api/health` and shows the readiness result.

## Apply the schema

The Docker Compose database does not run Alembic migrations automatically. To create the application
schema in a configured database, run from `backend/`:

```bash
uv run alembic upgrade head
```

See [../DATABASE.md](../DATABASE.md) before using the Aiven-only bootstrap SQL file.
