# System Architecture — Kontexa

This document describes the high-level system architecture, component boundaries, and technical principles governing Kontexa.

---

## High-Level Architecture Overview

```text
                    ┌──────────────────────┐
                    │      Frontend        │
                    │ Next.js / React / TS │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │       Backend        │
                    │ FastAPI / Python     │
                    │                      │
                    │ Modular Monolith     │
                    └───────┬───────┬──────┘
                            │       │
                            ▼       ▼
                     PostgreSQL    Redis
                      + pgvector
```

---

## 1. Current Architecture (Initialized Foundation)

The repository is structured as a **modular monolith monorepo**:

- **Frontend**: A Next.js (TypeScript, React, Tailwind CSS) web application providing the client workspace UI.
- **Backend**: A Python 3.12+ FastAPI application structured for domain modularity. Currently bootstrapped with core application settings, database session management, and a health endpoint (`GET /health`).
- **Data Stores**: Local Docker environment supporting PostgreSQL 16+ (with `pgvector` extension) and Redis.
- **Infrastructure**: Local developer orchestration via Docker Compose.

---

## 2. Intended Backend Module Boundaries

Future backend functionality will be developed as explicit modules inside `backend/src/kontexa/`:

```text
backend/src/kontexa/
├── api/             # FastAPI routing and endpoint handlers
├── core/            # Environment settings, security primitives, logging
├── database/        # Engine initialization, session management, migrations
│
├── auth/            # (Planned) Authentication and session management
├── projects/        # (Planned) Workspace project management
├── conversations/   # (Planned) Chat history and context session tracking
│
├── knowledge/       # (Planned) Document ingestion, parsing, chunking, indexing
├── ai/              # (Planned) LLM provider abstractions, prompts, tool definitions
├── memory/          # (Planned) Context tracking and long-term memory
└── integrations/    # (Planned) GitHub and third-party API integrations
```

*Note: The domain directories above represent architectural direction and are not created until active feature development requires them.*

---

## 3. Conceptual AI & RAG Pipeline (Planned Direction)

When context retrieval and AI feature development begins, knowledge processing will follow a pipeline:

```text
External Sources (Codebase, Docs, GitHub)
            ↓
Ingestion & Parsing
            ↓
Knowledge Representation (Embeddings / Chunking)
            ↓
Vector Retrieval (PostgreSQL + pgvector)
            ↓
AI / LLM Processing
            ↓
Application Response
```

*Clarification: No AI, embedding generation, or vector retrieval logic is active in the initialized repository.*

---

## 4. Key Architectural Principles

1. **Modular Monolith First**: Build features as well-defined internal backend modules before considering distributed services.
2. **PostgreSQL as Primary Data Store**: Store relational application data and vector embeddings within PostgreSQL (leveraging `pgvector`).
3. **Targeted Redis Usage**: Use Redis strictly for session caching, rate-limiting, or task queue backends where technically justified.
4. **Strict Vendor Isolation**: Wrap all external AI and LLM APIs behind internal interfaces to prevent vendor lock-in across domain logic.
5. **Measurable Complexity**: Only add abstractions or microservices when technical requirements demand them.
