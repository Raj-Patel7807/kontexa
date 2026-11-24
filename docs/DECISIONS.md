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

---

## ADR-009: Phased Connector Strategy with GitHub as Deep MVP Connector
- **Status**: Accepted
- **Context**: The long-term product vision encompasses a wide ecosystem (code, chat, email, project management, wikis, and observability). Attempting to build 10+ connectors simultaneously in the first release would result in shallow, fragile integrations that provide minimal developer value.
- **Decision**: Focus first-release engineering strictly on GitHub as a deep connector (repository sync, AST symbol extraction, commit history, file/line citations, and draft PR creation), accompanied by exactly one secondary connector (Linear or Jira) to demonstrate cross-source context correlation. Defer Slack, Discord, Notion, Confluence, Gmail, Outlook, Sentry, Datadog, and additional VCS providers to subsequent phases.
- **Consequences**:
  - *Positive*: Delivers a cohesive, high-utility developer experience for code intelligence before expanding integration breadth; limits security attack surface and OAuth management complexity.
  - *Negative*: Users requesting communication or observability connectors must wait for subsequent phases.

---

## ADR-010: Server-Sent Events (SSE) for Real-Time Streaming
- **Status**: Accepted
- **Context**: The conversational assistant requires real-time token streaming to deliver responsive UX with minimal time-to-first-token. Transport candidates include WebSockets, Server-Sent Events (SSE), and HTTP chunked transfer.
- **Decision**: Adopt Server-Sent Events (SSE) via `text/event-stream` over standard HTTP.
- **Consequences**:
  - *Positive*: Works out-of-the-box over standard HTTP/2, corporate firewalls, and Vercel proxy rewrites; passes standard HttpOnly session cookies without custom handshake auth; native browser reconnect handling via `EventSource`; half-duplex nature matches the request-response conversational pattern.
  - *Negative*: Unidirectional from server to client; client cancellations require an explicit HTTP cancellation request or socket drop.

---

## ADR-011: HttpOnly Secure Cookie-Based Session Architecture with Redis Lookup
- **Status**: Accepted
- **Context**: Authentication tokens stored in browser `localStorage` or `sessionStorage` are vulnerable to exfiltration via Cross-Site Scripting (XSS). Pure stateless JWTs cannot be revoked immediately upon logout or compromise.
- **Decision**: Issue random, cryptographically secure 256-bit session tokens stored in `HttpOnly`, `SameSite=Lax`, `Secure` browser cookies. Cache session profiles in Redis (900-second sliding TTL) with PostgreSQL backup.
- **Consequences**:
  - *Positive*: Complete immunity against JavaScript-based token theft (XSS); instant session revocation via `redis.delete()`; sub-millisecond session validation on hot requests.
  - *Negative*: Requires stateful session management and Redis availability.

---

## ADR-012: Decoupled Worker Process for Background Tasks
- **Status**: Accepted
- **Context**: Operations such as repository synchronization, AST symbol parsing, document embedding, and sandboxed test execution require significant CPU and wall-clock time (10s to 5 minutes). Running these inside FastAPI async request handlers blocks event loops and triggers HTTP gateway timeouts.
- **Decision**: Run a dedicated background worker process sharing the codebase, PostgreSQL database, and Redis task queue. The web API enqueues tasks; the worker executes them asynchronously.
- **Consequences**:
  - *Positive*: Web API maintains sub-100ms response times; workers can be scaled independently on Render/Railway based on queue depth; sandbox execution failures cannot crash the web API.
  - *Negative*: Requires running and monitoring a secondary container process in deployment.

---

## ADR-013: Hybrid Vector and Lexical Retrieval Strategy with RRF
- **Status**: Accepted
- **Context**: Pure vector search struggles with exact code identifiers, class names, and error strings (e.g. `test_models_initialization`). Pure lexical search fails on conceptual queries (e.g. "how are session tokens verified").
- **Decision**: Implement hybrid retrieval combining `pgvector` cosine similarity search with PostgreSQL trigram (`pg_trgm`) and full-text search (`tsvector`), merged via Reciprocal Rank Fusion (RRF).
- **Consequences**:
  - *Positive*: Superior recall and precision across both conceptual questions and exact code symbol inquiries; all search operations remain within the single PostgreSQL database.
  - *Negative*: Requires creating and maintaining both vector IVFFlat indexes and GIN/trigram text indexes.

---

## ADR-014: Two-Phase Hash-Bound Agent Approval Model
- **Status**: Accepted
- **Context**: Allowing autonomous AI agents to modify code, execute terminal commands, or push git branches without human review creates intolerable risks of hallucination, accidental deletion, or prompt injection exploitation.
- **Decision**: Enforce a mandatory two-phase workflow for all mutating agent tasks:
  1. *Planning Phase*: The agent generates an execution manifest (diff hunks, file targets, shell commands) and computes `plan_hash = SHA256(canonical_manifest)`.
  2. *Execution Phase*: Execution is rejected unless the developer submits a signed approval containing the identical `plan_hash`.
- **Consequences**:
  - *Positive*: Cryptographically guarantees that what the developer saw and approved is strictly what executes; prevents unauthorized drift or command injection.
  - *Negative*: Requires an interactive UI approval step, preventing fully autonomous unattended execution.

---

## ADR-015: URL Path-Based API Versioning (`/api/v1/`)
- **Status**: Accepted
- **Context**: System contracts must evolve predictably without breaking web clients or integrations.
- **Decision**: Prefix all domain, entity, and product endpoints with `/api/v1/`. Health checks retain `/health` and `/api/v1/health`.
- **Consequences**:
  - *Positive*: Explicit contract boundaries, straightforward router modularity in FastAPI, clear deprecation path for future breaking changes.
  - *Negative*: URL paths include explicit version segments.
