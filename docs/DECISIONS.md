# Architecture Decision Records (ADRs)

This document records the foundational architecture and engineering decisions established for Kontexa.

---

## ADR-001: Modular Monolith Backend Architecture
- **Status**: Accepted
- **Context**: The product requires complex coordination across authentication, conversations, document retrieval, and external connectors. Splitting into microservices introduces distributed transactions, RPC overhead, complex deployment, and network failure modes.
- **Decision**: Build the Kontexa backend as a single FastAPI modular monolith (`backend/src/kontexa/`). Domain modules (auth, workspaces, chat, rag, connectors, agent) maintain explicit interfaces and layers.
- **Consequences**:
  - *Positive*: Simple local development, single database transaction boundary, unified migration history, easy deployment on single container host (Render / Railway).
  - *Negative*: Developers must enforce internal boundaries strictly to prevent circular dependencies.

---

## ADR-002: PostgreSQL 16 with pgvector for Relational and Vector Data
- **Status**: Accepted
- **Context**: Kontexa requires relational tables for users, workspaces, projects, and conversations, along with vector similarity search for document and code chunks. Using a standalone vector database (e.g. Pinecone, Qdrant) requires dual-database transactions and data synchronization.
- **Decision**: Use PostgreSQL 16 with the `pgvector` extension for both relational records and embedding vectors.
- **Consequences**:
  - *Positive*: Atomic transactions across relational entities and vector chunks, ACID guarantees, single backup and restore pipeline (Aiven managed PostgreSQL).
  - *Negative*: Large-scale vector indexing requires tuning PostgreSQL memory parameters (`maintenance_work_mem`, IVFFlat/HNSW lists).

---

## ADR-003: Targeted Redis Utilization
- **Status**: Accepted
- **Context**: A fast in-memory store is needed for short-lived operational concerns, but persisting critical application state in Redis introduces data loss risks.
- **Decision**: Restrict Redis to short-lived caching, session token storage, rate-limiting counters, and job queues. PostgreSQL remains the sole permanent system of record.
- **Consequences**:
  - *Positive*: Clean separation between volatile cache and durable storage; Redis can be flushed or restarted without data loss.

---

## ADR-004: Monorepo Layout with Next.js 16 and FastAPI
- **Status**: Accepted
- **Context**: Frontend (web client) and Backend (API) evolve tightly together during rapid iterative feature sprints.
- **Decision**: Maintain both in a single repository: `frontend/` (Next.js 16 App Router, React 19, TypeScript, Tailwind CSS v4) and `backend/` (FastAPI, Python 3.12+, uv).
- **Consequences**:
  - *Positive*: Atomic cross-stack commits, unified PR review, simplified Docker Compose orchestration.
  - *Negative*: Tooling must accommodate both Node.js and Python ecosystems.

---

## ADR-005: Provider-Independent AI Gateway Boundary
- **Status**: Accepted
- **Context**: Hardcoding vendor SDKs (e.g. `openai` or `anthropic`) directly into conversation or retrieval domain logic couples the codebase to specific model providers and prevents seamless failover or local testing.
- **Decision**: Isolate all LLM and embedding invocations behind an internal gateway abstraction (`AIGateway` interface). Domain modules receive typed responses without knowing the underlying vendor.
- **Consequences**:
  - *Positive*: Enables switching models via configuration, mockable test providers for CI, and multi-provider load balancing.
  - *Negative*: Internal abstraction must normalize streaming events and token usage formats across vendors.

---

## ADR-006: Alembic Migrations as Sole Database Source of Truth
- **Status**: Accepted
- **Context**: Static SQL scripts can drift from SQLAlchemy ORM models if maintained separately.
- **Decision**: Alembic migrations under `backend/migrations/versions/` are the sole authoritative source of truth for the database schema. `infrastructure/database/schema.sql` is strictly for bootstrapping empty instances and must be verified against Alembic.
- **Consequences**:
  - *Positive*: Version-controlled, reversible schema evolution tested in CI.
  - *Negative*: Every schema change requires generating and verifying an Alembic migration.

---

## ADR-007: Strict Truthfulness & Status Classification Policy
- **Status**: Accepted
- **Context**: Complex AI projects frequently suffer from "documentation debt" where documentation claims features exist when only database tables or dummy UI screens are present.
- **Decision**: Enforce four strict status labels across all documentation: **`Implemented`**, **`Partial`**, **`Planned`**, and **`Deprecated`**. Never label a feature as `Implemented` unless it has functional user-reachable code and automated test coverage.
- **Consequences**:
  - *Positive*: Eliminates ambiguity for developers, contributors, and reviewers; ensures complete transparency.
  - *Negative*: Requires disciplined updates to docs during every sprint.

---

## ADR-008: Human-in-the-Loop Control for Agent Write Actions
- **Status**: Accepted
- **Context**: Autonomous AI agents modifying code or external systems without human review introduce security risks, repository corruption, and unintended side effects.
- **Decision**: All agent actions are read-only by default. Any write action (editing code, pushing git branches, creating draft pull requests, updating tickets) requires an explicit human approval step cryptographically bound to an immutable plan hash.
- **Consequences**:
  - *Positive*: Prevents hallucinated commands or unauthorized mutations; safe for sensitive repositories.
  - *Negative*: Requires UI approval flows and prevents 100% hands-off automation.
