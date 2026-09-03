# Roadmap

This roadmap sequences intended product work. It is not an implementation tutorial and does not
change the source of truth for current behavior: the repository and its tests do that. See
[PRD.md](PRD.md) for product scope and [ARCHITECTURE.md](ARCHITECTURE.md) for boundaries.

## Completed foundation

The repository currently includes:

- a Next.js status dashboard and a FastAPI readiness API;
- PostgreSQL and Redis health checks;
- async SQLAlchemy/Redis clients, an initial ORM model set, and Alembic migration;
- PostgreSQL 16 with pgvector, Redis 7, backend, and frontend Docker Compose services;
- backend pytest/Ruff and frontend ESLint/typecheck/build CI checks.

The initial schema is present, but it does not make user-facing authentication, project management,
chat, RAG, integrations, or tools available.

## Next: authentication and tenancy

Implement identity, session handling, authorization, and the workspace membership checks required
to protect tenant-scoped data. This should establish clear ownership and data-isolation behavior
before product APIs expose workspace data.

## Then: workspace and project workflows

Build the API and UI for creating, selecting, and managing workspaces and projects. Use the
existing persistence model only after authorization rules and migration behavior are verified.

## Then: conversations and AI responses

Add persistent conversation and message workflows, a provider-independent LLM boundary, and a
chat interface. Decide and document the streaming contract before presenting streamed responses as
an available capability.

## Then: knowledge, memory, and retrieval

Add document ingestion, versioning, chunking, embeddings, vector retrieval, and bounded memory
workflows. pgvector is available in the schema and local image, but no embedding, ingestion, or
retrieval code currently exists.

## Later: integrations, tools, and governance

Evaluate GitHub and other integrations, controlled tool execution, citations, usage tracking, and
audit logging as product capabilities. The schema reserves relevant entities; their security model,
API contracts, and operational limits remain to be designed.

## Planning principles

- Keep planned capabilities explicitly distinct from implemented behavior.
- Prefer a modular monolith and explicit internal boundaries.
- Add dependencies, infrastructure, and abstraction only when a concrete feature needs them.
- Record material architecture choices in [DECISIONS.md](DECISIONS.md).
