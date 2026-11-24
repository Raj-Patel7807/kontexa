# Feature Status Audit Matrix

This document provides a truthful, evidence-backed status report of all system capabilities in the Kontexa repository.

---

## Status Classification

- **`Implemented`**: Code exists, is user-reachable or API-reachable, and is verified by automated tests.
- **`Partial`**: Scaffolding, database models, or infrastructure components exist, but complete user-reachable workflows are missing.
- **`Planned`**: Designed in PRD / Roadmap for future sprints; no active user-facing implementation exists.
- **`Deprecated`**: Superseded or removed legacy artifacts.

---

## Audit Matrix

| Domain | Capability | Status | Evidence in Codebase | Notes / Missing Work |
| :--- | :--- | :---: | :--- | :--- |
| **Foundation** | Backend FastAPI Factory | **Implemented** | `backend/src/kontexa/main.py` | Complete app factory, CORS middleware, lifespan management. |
| **Foundation** | Pydantic Settings & TLS | **Implemented** | `backend/src/kontexa/core/config.py` | Typed settings, Aiven SSL context generation. Covered in `test_config.py`. |
| **Foundation** | Health & Readiness Checks | **Implemented** | `backend/src/kontexa/api/health.py`, `core/health.py` | Concurrent PostgreSQL & Redis ping, latency tracking, 503 on failure. Covered in `test_health.py`. |
| **Infrastructure** | Docker Compose Stack | **Implemented** | `infrastructure/docker/docker-compose.yml` | PostgreSQL 16 (pgvector), Redis 7, backend, and frontend containers configured. |
| **Infrastructure** | Continuous Integration | **Implemented** | `.github/workflows/ci.yml` | Backend lint/format/test, frontend lint/typecheck/build, Compose integration checks. |
| **Frontend** | Landing Page Web UI | **Partial** | `frontend/src/app/page.tsx` | Next.js 16 App Router landing page. Clean Turbopack build and linting. Live health dashboard was removed in prior commit; product UI is not connected to APIs. |
| **Database** | Database ORM Models | **Partial** | `backend/src/kontexa/database/models/` | 18 SQLAlchemy 2.0 tables mapped and tested (`test_models.py`), but no domain services read/write them yet. |
| **Database** | Alembic Migrations | **Partial** | `backend/migrations/versions/` | Initial schema (`20260811_0001`) and hardening (`20260904_0002`). Applied in Docker CI, but no domain data populates them. |
| **Database** | pgvector Vector Storage | **Partial** | `backend/src/kontexa/database/models/documents.py` | `document_chunks.embedding` column with IVFFlat index is defined in schema; embedding generation and vector search are not implemented. |
| **Database** | Redis Client Connection | **Partial** | `backend/src/kontexa/database/redis.py` | Redis connection check works for health endpoints; caching, session storage, and queues are not implemented. |
| **Auth & Tenancy** | User Auth & Sessions | **Planned** | `backend/src/kontexa/database/models/users.py` (model only) | Zero auth endpoints, JWT/session handling, password hashing, or auth middleware exist. Scheduled for Sprint 07. |
| **Auth & Tenancy** | Workspace & Project Management | **Planned** | `backend/src/kontexa/database/models/workspaces.py`, `projects.py` | Schema exists; zero CRUD endpoints, membership enforcement, or tenant validation exist. Scheduled for Sprint 08. |
| **Chat & AI** | Persistent Conversations | **Planned** | `backend/src/kontexa/database/models/conversations.py`, `messages.py` | Schema exists; zero conversation endpoints, history rendering, or message APIs exist. Scheduled for Sprint 10. |
| **Chat & AI** | AI Provider Gateway & Streaming | **Planned** | `backend/src/kontexa/database/models/ai.py` (model only) | Zero LLM provider adapters, streaming SSE contracts, or token accounting logic exist. Scheduled for Sprints 11–12. |
| **Knowledge** | Document Ingestion & Chunking | **Planned** | `backend/src/kontexa/database/models/documents.py` (model only) | Zero upload handlers, parsers, chunking pipelines, or hash deduplication exist. Scheduled for Sprint 13. |
| **Knowledge** | Hybrid Retrieval & Citations | **Planned** | `document_chunks` table with pgvector (schema only) | Zero vector queries, reranking, or file/line citation logic exist. Scheduled for Sprint 14. |
| **Connectors** | GitHub Repository Intelligence | **Planned** | None | No GitHub App, webhook, or repository indexing code exists. Scheduled for Sprints 15–18. |
| **Agent Tasks** | Sandboxed Execution & Tool Runs | **Planned** | `backend/src/kontexa/database/models/tools.py` (model only) | Zero sandbox execution, approval hash validation, or tool dispatchers exist. Scheduled for Sprints 19–21. |
| **Cross-Source** | Context Graph & Second Connector | **Planned** | `memory_entries`, `audit_logs` (models only) | Zero cross-source correlation or audit logging producers exist. Scheduled for Sprints 22–25. |

---

## Known Discrepancies Resolved in Sprint 01

1. **Frontend Health Dashboard Discrepancy**:
   - *Previous Documentation Claim*: Stated that the frontend web UI at `/` actively polls `/api/health` every 15 seconds and displays backend, PostgreSQL, and Redis status.
   - *Actual Implementation*: The health polling dashboard was replaced in commit `d44dd0b9` with a static marketing landing page.
   - *Resolution*: Documentation updated to correctly mark frontend product UI as **`Partial`** and document that the landing page is static, while the backend health API remains fully **`Implemented`** and tested.

2. **Schema Models vs Feature State**:
   - *Previous State*: 18 database tables exist in SQLAlchemy models and migrations, which could lead an observer to assume features like chat, document retrieval, and tool execution exist.
   - *Resolution*: All 18 tables are explicitly cataloged as **`Partial`** persistence foundations. All associated business workflows and APIs are confirmed as **`Planned`**.
