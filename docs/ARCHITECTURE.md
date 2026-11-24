# System Architecture

## 1. Architectural Philosophy: The Modular Monolith

Kontexa is architected as a **Modular Monolith**. All core backend domain logic (authentication, workspace tenancy, chat orchestration, knowledge retrieval, connector integrations, tool dispatch, and audit logging) lives within a single FastAPI application package (`backend/src/kontexa/`).

We deliberately avoid premature microservice decomposition:
- **Simplicity**: Single codebase, unified migration pipeline, straightforward local orchestration, and zero distributed transaction overhead.
- **Strict Domain Boundaries**: Modules communicate via clearly defined Python interfaces and dependency injection rather than internal network calls.
- **Independent Scalability**: If a specific compute-heavy workload emerges (such as background repository parsing or sandboxed code execution), it will be extracted into a dedicated worker service sharing the same database and Redis message broker, not a microservice.

---

## 2. Current vs. Planned Architecture

### Current Implemented Architecture (Sprint 01)

The system currently operates a verified baseline application foundation:

```mermaid
flowchart TD
    subgraph Client["Client Tier"]
        Browser["Browser / Developer"]
    end

    subgraph FrontendApp["Frontend Tier (Next.js 16)"]
        NextUI["App Router Landing Page (:3000)"]
        NextRewrite["API Rewrite Proxy (/api/:path*)"]
    end

    subgraph BackendApp["Backend Tier (FastAPI)"]
        AppFactory["FastAPI App Factory & Middleware (:8000)"]
        Config["Pydantic Settings (Aiven TLS/SSL)"]
        HealthRouter["Health & Readiness Endpoints (/health, /api/v1/health)"]
        HealthService["Concurrent Component Health Checker"]
    end

    subgraph DataTier["Data & Cache Tier"]
        PostgresDB[("PostgreSQL 16 + pgvector<br/>(18-table ORM schema registered)")]
        RedisCache[("Redis 7<br/>(Ping check active)")]
    end

    Browser -->|HTTP GET /| NextUI
    Browser -.->|API Requests| NextRewrite
    NextRewrite -.->|Proxy Rewrite| AppFactory
    AppFactory --> HealthRouter
    HealthRouter --> HealthService
    HealthService -->|SELECT 1| PostgresDB
    HealthService -->|PING| RedisCache
```

- **Frontend**: Next.js 16 (React 19, TypeScript, Tailwind CSS v4) configured with an App Router landing page and an API rewrite in `next.config.ts`.
- **Backend**: FastAPI modular application exposing `GET /health` and `GET /api/v1/health`.
- **Database**: PostgreSQL 16 with `pgvector`, `uuid-ossp`, and `pgcrypto` extensions. 18 SQLAlchemy models mapped and migrated via Alembic.
- **Cache**: Redis 7 verifying sub-millisecond connectivity.

---

### Target Architecture (Phase 2–Phase 7)

```mermaid
flowchart TD
    subgraph ClientLayer["Clients"]
        BrowserUI["Kontexa Web App (Next.js 16)"]
    end

    subgraph BackendMonolith["FastAPI Modular Monolith"]
        APIGateway["FastAPI HTTP / SSE Engine"]
        
        subgraph Domains["Core Domain Modules"]
            AuthModule["Auth & Session Domain"]
            WorkspaceModule["Workspace & Tenancy Domain"]
            ChatModule["Conversation & Chat Domain"]
            AIGatewayModule["Provider-Agnostic AI Gateway"]
            KnowledgeModule["Document Ingestion & RAG"]
            ConnectorModule["Connector Engine (GitHub / Jira)"]
            AgentModule["Agent Orchestrator & Tool Registry"]
            AuditModule["Audit & Security Event Logger"]
        end

        subgraph CoreInfra["Core Infrastructure"]
            DBSession["Async SQLAlchemy Session"]
            RedisClient["Redis Connection & Cache"]
            SettingsMgr["Settings & Vault"]
        end
    end

    subgraph DataStorage["Persistence & Cache"]
        PostgreSQL[("PostgreSQL 16<br/>Relational Data + pgvector Chunks")]
        RedisStore[("Redis 7<br/>Sessions, Caching & Job Queues")]
    end

    subgraph ExternalServices["External Ecosystem"]
        LLMProviders["AI Providers (OpenAI, Anthropic, Gemini)"]
        GitHubAPI["GitHub API / Webhooks"]
        ExtTools["Secondary Connectors (Linear, Slack, Jira)"]
    end

    subgraph Sandbox["Isolated Execution"]
        WorkerSandbox["Sandboxed Workspace Runner (Docker)"]
    end

    BrowserUI -->|REST / SSE Streaming| APIGateway
    APIGateway --> Domains
    Domains --> CoreInfra
    CoreInfra --> DataStorage
    AIGatewayModule -->|HTTPS| LLMProviders
    ConnectorModule -->|OAuth / Webhooks| GitHubAPI
    ConnectorModule -->|REST API| ExtTools
    AgentModule -->|Isolated Execution| WorkerSandbox
```

---

## 3. Trust Boundaries & Security Zones

1. **Client / Browser Zone**:
   - Untrusted environment.
   - Holds only short-lived session cookies or JWT tokens.
   - Never receives provider API keys, database credentials, or tenant access keys.
2. **Edge / API Gateway Boundary**:
   - Validates all incoming payloads via Pydantic schemas.
   - Validates authentication and active workspace membership.
   - Rejects unauthorized cross-tenant requests before hitting domain services.
3. **Internal Domain Layer**:
   - Strictly typed domain services.
   - Parameterized queries to prevent SQL injection.
   - Retains context isolation between workspaces.
4. **External Provider Zone**:
   - AI provider APIs, GitHub API, and third-party tools.
   - Outbound requests use least-privilege tokens stored with encryption.
   - Incoming data is treated as untrusted (prompt injection defense).
5. **Execution Sandbox**:
   - Dedicated, resource-limited environment for running user-approved agent development tasks and tests.
   - Isolated from host filesystem, networks, and internal cloud metadata endpoints.

---

## 4. Deployment Posture

- **Local Development**: Fully orchestrated via `infrastructure/docker/docker-compose.yml` (PostgreSQL 16 with pgvector, Redis 7, Backend, and Frontend).
- **Target Production Environment**:
  - **Frontend**: Vercel (Next.js serverless/edge deployment).
  - **Backend API**: Render or Railway (containerized FastAPI service with health/readiness checks).
  - **Database**: Aiven PostgreSQL with pgvector (managed TLS/SSL with CA certificate validation).
  - **Cache**: Managed Redis (Aiven / Upstash).
