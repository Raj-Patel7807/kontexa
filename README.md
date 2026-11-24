# Kontexa

**Kontexa** is an AI Software Engineering Workspace designed to unify context across a developer's engineering ecosystem — code, documentation, communication, and project management — and assist engineers in understanding, investigating, and performing development tasks with evidence and human control.

> [!IMPORTANT]
> **Current Status Notice**: Kontexa is currently in active foundational development. The repository contains a production-ready application foundation (FastAPI modular monolith, 18-table SQLAlchemy 2.0 / Alembic database schema with pgvector, Redis health verification, Docker Compose stack, CI pipelines, and a Next.js 16 frontend landing page). Core product capabilities such as authentication, workspace management, streamed chat, document ingestion/RAG, GitHub repository intelligence, and sandboxed task execution are **Planned** across upcoming sprints.

---

## Status Classification

To maintain absolute transparency between documentation and actual implementation, Kontexa strictly enforces four status labels across all documentation:

- **`Implemented`**: Fully operational in code, reachable via user interface or active API endpoints, covered by passing automated tests.
- **`Partial`**: Scaffolding, database models, or infrastructure components exist in the repository, but user-facing or end-to-end workflows are incomplete.
- **`Planned`**: Designed in PRD and Roadmap; no working user-reachable implementation exists yet.
- **`Deprecated`**: Superseded or removed legacy artifacts.

For a full granular status breakdown of all features, see [docs/FEATURE_STATUS.md](docs/FEATURE_STATUS.md).

---

## Repository Structure

```text
kontexa/
├── backend/                 # FastAPI modular monolith API, models, migrations & tests
│   ├── migrations/          # Alembic schema migrations (source of truth for DB schema)
│   ├── src/kontexa/         # Core application package
│   │   ├── api/             # API routes (health endpoints active)
│   │   ├── core/            # App configuration and health services
│   │   └── database/        # Async SQLAlchemy session, Redis client, and 18 ORM models
│   └── tests/               # Pytest suite (unit & integration: 89 passed tests)
├── frontend/                # Next.js 16 App Router web interface (React 19, TypeScript, Tailwind CSS v4)
├── infrastructure/          # Docker & database provisioning assets
│   ├── database/            # Standalone SQL bootstrap script (Aiven reference)
│   └── docker/              # Dockerfiles and local Docker Compose stack
├── docs/                    # Complete product, architecture, and engineering documentation
└── scripts/                 # Developer support utilities
```

---

## Quick Start

### Prerequisites

- **Python 3.12+** with [`uv`](https://docs.astral.sh/uv/)
- **Node.js 20+** and **npm**
- **Docker** and **Docker Compose**
- *(Optional)* GNU Make (on Linux/macOS)

### 1. Configure Environment

Copy example environment configuration files:

```bash
# On Linux / macOS
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# On Windows (PowerShell)
Copy-Item .env.example .env
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
```

> In `backend/.env`, ensure `DATABASE_URL` is uncommented for local backend development (default: `postgresql+asyncpg://kontexa:kontexa_pass@localhost:5432/kontexa_db`).

### 2. Install Dependencies

```bash
# Using Make
make setup

# Or directly:
cd backend && uv sync
cd ../frontend && npm install
```

### 3. Start Local Containerized Services

```bash
# Start PostgreSQL (with pgvector), Redis, Backend, and Frontend
make up

# Or via Docker Compose directly:
docker compose -f infrastructure/docker/docker-compose.yml up -d
```

### 4. Run Development Servers Locally

If running outside Docker:

```bash
# Backend (from backend directory)
cd backend
uv run uvicorn kontexa.main:app --reload --port 8000

# Frontend (from frontend directory)
cd frontend
npm run dev
```

### 5. Run Verification Checks

```bash
# Using Make
make check     # Full repository validation (lint, typecheck, test)
make lint      # Code style checks
make typecheck # Static type checks (mypy + tsc)
make test      # Pytest and frontend tests
make build     # Next.js production build

# Or directly:
# Backend
cd backend
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest

# Frontend
cd frontend
npm run lint
npm run typecheck
npm test
npm run build
```

---

## Documentation Index

Comprehensive documentation is maintained in the [`docs/`](docs/README.md) directory:

- **Product Specifications**:
  - [PRD (Product Requirements Document)](docs/PRD.md)
  - [Roadmap (28-Sprint Sequence)](docs/ROADMAP.md)
  - [Feature Status Audit Matrix](docs/FEATURE_STATUS.md)
- **Architecture & System Design**:
  - [System Architecture](docs/ARCHITECTURE.md)
  - [System & Product Flows](docs/FLOW.md)
  - [Database Architecture & Schema](docs/DATABASE.md)
  - [Architecture Decision Records (ADRs)](docs/DECISIONS.md)
- **Engineering & Operations**:
  - [API Specification](docs/API.md)
  - [Code Rules & Standards](docs/CODE_RULES.md)
  - [Security Architecture & Threat Model](docs/SECURITY.md)
  - [Configuration Reference](docs/CONFIGURATION.md)
  - [Local Development Setup](docs/development/setup.md)
  - [Testing Guide](docs/development/testing.md)

---

## License

Kontexa is licensed under the [Apache License 2.0](LICENSE).
