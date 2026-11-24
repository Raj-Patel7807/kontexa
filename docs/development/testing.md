# Testing & Verification Guide

This document defines testing workflows, verification commands, and CI pipelines for Kontexa.

---

## 1. Quick Verification Commands

From repository root:

```bash
# Full repository validation (lint, typecheck, test)
make check

# Or individual targets:
make lint        # Ruff lint (backend) & ESLint (frontend)
make typecheck   # Mypy (backend) & tsc (frontend)
make test        # Pytest (backend) & npm test (frontend)
make format      # Ruff auto-format (backend)
make build       # Next.js production build (frontend)
make migrate     # Alembic database migration (backend)
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

### 3. Mypy Static Type Check
```bash
uv run mypy
```
Enforces strict type annotations, return types, and argument validation across all backend packages.

### 4. Alembic Migration Consistency Check
```bash
uv run alembic heads
```
Verifies migration revision history resolves cleanly without branch conflicts.

### 5. Pytest Test Suite
```bash
uv run pytest
```
Current test suite covers:
- `tests/unit/test_config.py`: Settings validation, SSL context generation, connection args (10 tests).
- `tests/unit/test_health.py`: Health API readiness, degraded states, latency measurement (3 tests).
- `tests/unit/test_models.py`: All 18 SQLAlchemy ORM models, tables, columns, constraints (73 tests).
- `tests/unit/test_worker.py`: Background worker service lifecycle, dependency verification, graceful shutdown (4 tests).
- `tests/integration/test_database.py`: Session initialization, table discovery, schema.sql parity (3 tests).
- Total: **93 passed tests**.

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

### 3. Frontend Test Suite
```bash
npm test
```

### 4. Next.js Production Build
```bash
npm run build
```

---

## 4. Continuous Integration (GitHub Actions)

The CI pipeline (`.github/workflows/ci.yml`) executes four parallel workflow jobs on pushes and pull requests to `main`:

1. **`Secret Scanning`** (`.github/workflows/ci.yml`):
   - Uses `gitleaks/gitleaks-action@v2` to scan full git history for leaked credentials, private keys, or API tokens.
2. **`Backend CI`** (`.github/workflows/backend.yml`):
   - Sets up Python 3.12 with `astral-sh/setup-uv@v3` (dependency caching enabled).
   - Installs backend dependencies from `backend/uv.lock` via `uv sync --locked`.
   - Runs `ruff check .` (linter).
   - Runs `ruff format --check .` (formatter check).
   - Runs `mypy` (static type checker).
   - Runs `alembic heads` (migration consistency check).
   - Runs `pytest` (test suite).
3. **`Frontend CI`** (`.github/workflows/frontend.yml`):
   - Sets up Node.js 20 with `actions/setup-node@v4` (`npm` dependency caching enabled).
   - Installs dependencies from `frontend/package-lock.json` via `npm ci`.
   - Runs `npm run lint` (ESLint).
   - Runs `npm run typecheck` (`tsc --noEmit`).
   - Runs `npm test` (test suite).
   - Runs `npm run build` (Next.js production build).
4. **`Infrastructure CI`** (`.github/workflows/infrastructure.yml`):
   - Validates `infrastructure/docker/docker-compose.yml` config.
   - Builds container images for backend and frontend.
   - Starts PostgreSQL 16 (pgvector) and Redis 7 containers.
   - Applies Alembic migrations (`uv run alembic upgrade head`) to clean PostgreSQL database.
   - Starts application containers: `backend`, `worker`, and `frontend`.
   - Executes HTTP curl health probes against `http://localhost:8000/health` and `http://localhost:3000/`.
   - Cleans up containers and volumes.
