# Kontexa

Kontexa is an early-stage AI workspace for software engineers. It is intended to help teams
understand codebases, retain useful context, and support developer workflows in project-scoped
workspaces.

## Current status

The repository provides an engineering foundation rather than the finished product. Today it
includes a Next.js status dashboard, a FastAPI readiness API, PostgreSQL and Redis connectivity
checks, an initial PostgreSQL schema, local Docker Compose orchestration, and CI checks.

Authentication, workspace and project APIs, chat, AI-provider calls, document ingestion, and RAG
are planned; their database tables do not mean those product capabilities are available yet.

## Repository layout

```text
backend/                 FastAPI application, Alembic migrations, and pytest tests
frontend/                Next.js application
infrastructure/database/ Manual schema for a new Aiven PostgreSQL service
infrastructure/docker/   Dockerfiles and local Docker Compose stack
docs/                    Product, architecture, development, and decision documentation
scripts/                 Small developer utilities
```

## Local development

See the [setup guide](docs/development/setup.md). The common commands are:

```bash
make setup
make up
make dev
make lint
make test
```

`make up` starts the complete containerized stack: PostgreSQL, Redis, backend, and frontend.
`make dev` starts the backend and frontend locally, so configure `backend/.env` first.

## Documentation

Start with the [documentation index](docs/README.md). It links the product requirements,
architecture, flows, configuration reference, database reference, roadmap, and decisions.

## License

Distributed under the [MIT License](LICENSE).
