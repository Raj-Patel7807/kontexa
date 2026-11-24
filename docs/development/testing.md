# Testing & Verification Guide

This document defines testing workflows, verification commands, and CI pipelines for Kontexa.

---

## 1. Quick Verification Commands

From repository root:

```bash
# Using Make
make lint
make test
make build
```

---

## 2. Backend Verification

Run from `backend/`:

### 1. Ruff Linter Check
```bash
uv run ruff check .
```

### 2. Ruff Formatter Check
```bash
uv run ruff format --check .
# To automatically format:
uv run ruff format .
```

### 3. Pytest Test Suite
```bash
uv run pytest
```
Current test suite covers:
- `tests/unit/test_config.py`: Settings validation, SSL context generation, connection args (10 tests).
- `tests/unit/test_health.py`: Health API readiness, degraded states, latency measurement (3 tests).
- `tests/unit/test_models.py`: All 18 SQLAlchemy ORM models, tables, columns, constraints (73 tests).
- `tests/integration/test_database.py`: Session initialization, table discovery, schema.sql parity (3 tests).
- Total: **89 passed tests**.

---

## 3. Frontend Verification

Run from `frontend/`:

### 1. ESLint Check
```bash
npm run lint
```

### 2. TypeScript Type Check
```bash
npm run typecheck
```

### 3. Next.js Production Build
```bash
npm run build
```

---

## 4. Continuous Integration (GitHub Actions)

The CI pipeline (`.github/workflows/ci.yml`) executes three parallel workflow jobs on pushes and pull requests to `main`:

1. **`Backend CI`** (`.github/workflows/backend.yml`):
   - Installs Python 3.12 and `uv`.
   - Runs `uv sync --locked`.
   - Runs `ruff check .` and `ruff format --check .`.
   - Runs `pytest`.
2. **`Frontend CI`** (`.github/workflows/frontend.yml`):
   - Sets up Node.js 20 with npm cache.
   - Runs `npm ci`.
   - Runs `npm run lint`.
   - Runs `npm run typecheck`.
   - Runs `npm run build`.
3. **`Infrastructure CI`** (`.github/workflows/infrastructure.yml`):
   - Validates `docker-compose.yml` config.
   - Builds container images.
   - Starts PostgreSQL and Redis containers.
   - Applies Alembic migrations (`uv run alembic upgrade head`) to a clean PostgreSQL instance.
   - Starts backend and frontend containers.
   - Executes HTTP curl health probes against `http://localhost:8000/health` and `http://localhost:3000/`.
   - Cleans up containers and volumes.
