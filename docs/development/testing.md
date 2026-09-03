# Testing and Verification

Run the repository's required checks from the root:

```bash
make lint
make test
```

`make lint` runs `uv run ruff check .` in `backend/` and `npm run lint` in `frontend/`. `make test`
runs `uv run pytest` in `backend/` and `npm run typecheck` in `frontend/`.

## Backend

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

`make format` runs `uv run ruff format .` for the backend. The test suite includes unit tests for
settings, health behavior, and SQLAlchemy models, plus an integration-level check that the engine
and schema registry initialize. It does not require a live PostgreSQL or Redis instance because
health dependency calls are mocked in endpoint tests.

## Frontend

```bash
cd frontend
npm run lint
npm run typecheck
npm run build
```

No frontend test runner is configured. `npm run build` is an additional production-build check; it
is not included in `make test`.

## Continuous integration

The root `CI Pipeline` workflow runs on pushes and pull requests to `main`. It invokes reusable
backend and frontend workflows. Backend CI runs dependency installation, Ruff linting, Ruff format
checking, and pytest. Frontend CI runs `npm ci`, ESLint, TypeScript type checking, and the Next.js
production build.
