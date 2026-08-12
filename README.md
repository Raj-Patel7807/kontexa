# Kontexa

Kontexa is an AI workspace for software engineers designed to streamline codebase understanding, context retrieval, and developer workflows.

## Status

Foundation / early development. The repository currently contains the core engineering foundation, project tooling, and containerization setup. Product features are not yet implemented.

## Tech Stack

- **Frontend**: Next.js, React, TypeScript, Tailwind CSS, ESLint
- **Backend**: Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic, `uv`, Ruff, `pytest`
- **Database & Storage**: PostgreSQL (with `pgvector`), Redis
- **Infrastructure & Tooling**: Docker, Docker Compose, Pre-commit, GitHub Actions

## Project Structure

```text
kontexa/
├── .github/          # CI/CD workflows and issue/PR templates
├── frontend/         # Next.js web application
├── backend/          # FastAPI backend (modular monolith)
├── packages/         # Reserved for shared internal libraries
├── infrastructure/   # Docker configurations and local services setup
├── docs/             # Technical architecture, code rules, and developer setup
└── scripts/          # Developer automation utility scripts
```

## Development

The project includes a root `Makefile` for common management commands:

```bash
# Install backend and frontend dependencies
make setup

# Start local Docker infrastructure (PostgreSQL + Redis)
make up

# Stop Docker infrastructure
make down

# Run backend pytest suite and frontend type checks
make test

# Run linter checks (Ruff & ESLint)
make lint

# Format backend codebase
make format
```

## Readiness endpoint

The backend exposes `GET /health` (and `GET /api/v1/health`) for operational checks. It verifies
PostgreSQL and Redis using the configured application connections, then returns the service version,
environment, UTC timestamp, and per-dependency latency. It returns HTTP 200 when ready and HTTP 503
with `"status": "degraded"` when either required dependency is unavailable.

## Documentation

Detailed repository documentation is available in the `docs/` directory:

- [Code Rules & Standards](docs/CODE_RULES.md)
- [System Architecture](docs/ARCHITECTURE.md)
- [Architecture Decision Records (ADRs)](docs/decisions/README.md)
- [Local Setup Guide](docs/development/setup.md)
- [Testing Guide](docs/development/testing.md)
- [Agent Instructions](AGENTS.md)

## License

Distributed under the [MIT License](LICENSE).
