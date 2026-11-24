# Repository Guidelines & Coding Agent Rules

All engineers and AI coding agents working on Kontexa must strictly adhere to the instructions in this document.

---

## 1. Source-of-Truth Hierarchy

When evaluating system behavior or resolving conflicts between documents and code:

1. **Actual Code and Alembic Migrations**: Primary source of truth for runtime behavior and schema.
2. **Automated Tests and CI Workflows**: Source of truth for verified invariants.
3. **API Schemas and OpenAPI Specifications**: Source of truth for boundary contracts.
4. **Current Architecture and Product Documentation** (`docs/`): Source of truth for product intent, boundaries, and roadmap.
5. **Sprint Prompts and Historical Notes**: Supporting planning context.

Never conceal a discrepancy between documentation and code. Acknowledge and reconcile it explicitly.

---

## 2. Core Engineering Principles

- **Inspect Before Editing**: Read relevant source code, tests, migrations, and docs before proposing or writing changes.
- **Preserve Working Implementation**: Do not rewrite sound existing code for stylistic or arbitrary preferences.
- **Modular Monolith**: Maintain all backend domains within a single FastAPI application. Do not introduce microservices without clear, measured operational necessity.
- **Strict Status Truthfulness**: Never claim a feature is `Implemented` unless user-reachable code is functional and covered by passing tests. Features with only database models or scaffolding must be marked `Partial` or `Planned`.
- **Layer Boundaries**:
  - Route handlers parse inputs, enforce authorization, and return response models. Business logic belongs in dedicated domain services.
  - Third-party AI/LLM SDKs must remain strictly behind provider domain abstractions.
  - Data persistence logic resides in `kontexa.database`.
- **Security & Authorization**:
  - Authorize requests at the backend edge. Never rely on frontend route hiding.
  - Every tenant-owned row must have explicit workspace scoping.
  - Parameterize all database queries. Never concatenate SQL strings.
  - Secrets and OAuth tokens must be encrypted at rest and never logged or exposed in client bundles.
  - External retrieved data is untrusted; protect against prompt injection. Write operations require human approval.
- **Indentation & Formatting**:
  - Python: 4-space indentation, 100-character line length, formatted and linted with Ruff.
  - TypeScript: 2-space indentation (or project ESLint default), strict type checking via `tsc --noEmit`.

---

## 3. Mandatory Workflow for Every Change

1. **Analyze**: Read requirements, inspect existing code, identify files to touch.
2. **Implement**: Build the smallest complete vertical slice. Keep interfaces typed and explicit.
3. **Test**: Write or update tests covering success, failure, validation, and boundary conditions.
4. **Verify**: Run the full verification suite before declaring complete.
5. **Synchronize Docs**: Update `docs/FEATURE_STATUS.md` and relevant design documents whenever behavior or contracts change.

---

## 4. Verification Commands

### Cross-Platform (Make)
```bash
make lint
make test
```

### Backend (Direct)
```bash
cd backend
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

### Frontend (Direct)
```bash
cd frontend
npm run lint
npm run typecheck
npm run build
```

---

## 5. Required Reading Before Modifying Code

- Read [docs/CODE_RULES.md](docs/CODE_RULES.md) before writing or refactoring code.
- Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/DATABASE.md](docs/DATABASE.md), and [docs/ROADMAP.md](docs/ROADMAP.md) before making architectural changes.
- Read [docs/SECURITY.md](docs/SECURITY.md) before modifying authentication, permissions, or external integrations.
