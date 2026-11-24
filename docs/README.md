# Kontexa Documentation Index

Welcome to the Kontexa technical documentation. This directory provides the definitive specifications, architecture designs, data models, engineering standards, and operational guidelines for Kontexa.

---

## 1. Documentation Source-of-Truth Hierarchy

To prevent divergence between written documentation and actual system capabilities:

1. **Code & Alembic Migrations**: Absolute source of truth for runtime behavior and database schema.
2. **Automated Tests & CI**: Source of truth for verified invariants and operational readiness.
3. **API Contracts**: Source of truth for input/output payloads and status codes.
4. **Current Documentation (`docs/`)**: Source of truth for architecture boundaries, design decisions, and requirements.
5. **Sprint Prompts & Notes**: Historical planning context.

---

## 2. Status Label Definitions

Every capability described in the documentation is labeled with one of four statuses:

- **`Implemented`**: Fully operational in code, reachable via user interface or active API endpoints, verified by automated tests.
- **`Partial`**: Scaffolding, database schema, or infrastructure components exist in the repository, but user-facing or complete end-to-end workflows are not yet functional or fully wired.
- **`Planned`**: Formally specified in the PRD and sequenced in the Roadmap; no working user-reachable implementation exists yet.
- **`Deprecated`**: Phased out or superseded legacy artifacts.

For the definitive audit matrix, see [FEATURE_STATUS.md](FEATURE_STATUS.md).

---

## 3. Directory Navigation

### Product Specifications
- [PRD.md](PRD.md) — Product requirements, user personas, problem statement, and MVP scope.
- [ROADMAP.md](ROADMAP.md) — Sequenced 28-sprint implementation plan and release phases.
- [FEATURE_STATUS.md](FEATURE_STATUS.md) — Truthful status matrix for every system feature with codebase evidence.

### Architecture & Design
- [ARCHITECTURE.md](ARCHITECTURE.md) — System boundaries, container structure, modular monolith design, and Mermaid diagrams.
- [FLOW.md](FLOW.md) — Sequence and flow diagrams for current health checks and planned product workflows.
- [DATABASE.md](DATABASE.md) — Relational schema, 18 SQLAlchemy models, pgvector indexing, and tenancy integrity.
- [DECISIONS.md](DECISIONS.md) — Architecture Decision Records (ADRs) explaining key technical choices and trade-offs.

### Engineering Standards & Contracts
- [API.md](API.md) — API conventions, active health endpoints (`GET /health`, `GET /api/v1/health`), and planned routes.
- [CODE_RULES.md](CODE_RULES.md) — Coding conventions, layer boundaries, typing, and error-handling standards.
- [SECURITY.md](SECURITY.md) — Threat model, tenant isolation, prompt injection defense, and credential security.
- [CONFIGURATION.md](CONFIGURATION.md) — Environment variable specifications for backend, frontend, and Docker Compose.

### Operations & Development
- [development/setup.md](development/setup.md) — Step-by-step developer setup for Linux, macOS, and Windows.
- [development/testing.md](development/testing.md) — Testing commands, CI workflows, and verification standards.
