# System & Product Flows

This document details both the currently implemented system flows and the planned product workflows.

---

## 1. Implemented System Flows (Sprint 01)

### A. Dependency Health & Readiness Check Flow

The backend exposes two active endpoints: `GET /health` and `GET /api/v1/health`. Both probe PostgreSQL and Redis concurrently with a configurable timeout guard (`HEALTH_CHECK_TIMEOUT_SECONDS`, default 2.0s).

```mermaid
sequenceDiagram
    autonumber
    participant Client as Client (Browser / Monitoring)
    participant Router as FastAPI Health Router
    participant Checker as Component Health Checker
    participant DB as PostgreSQL (asyncpg)
    participant Redis as Redis Client

    Client->>Router: GET /health (or /api/v1/health)
    Router->>Checker: check_component("database") & check_component("redis")
    par Database Probe
        Checker->>DB: SELECT 1
        DB-->>Checker: Success (latency recorded)
    and Redis Probe
        Checker->>Redis: PING
        Redis-->>Checker: PONG (latency recorded)
    end

    alt Both dependencies healthy
        Checker-->>Router: database: ok, redis: ok
        Router-->>Client: 200 OK { status: "ok", service: "kontexa", dependencies: { ... } }
    else Any dependency unavailable or timed out
        Checker-->>Router: e.g. redis: unavailable (error logged internally)
        Router-->>Client: 503 SERVICE UNAVAILABLE { status: "degraded", dependencies: { ... } }
    end
```

### B. Health Degradation & Information Hiding Flow

When a dependency probe encounters a connection failure, network timeout, or authorization error:
1. The error details, stack trace, and connection targets are logged strictly on the server at `ERROR` level.
2. The public API response masks all internal credentials, hosts, and raw exception messages.
3. The response payload returns `status: "unavailable"` with `latency_ms: 0.0` and HTTP status `503 Service Unavailable`.

---

## 2. Planned Product Flows

### A. Authentication & Session Verification Flow (Sprint 07)

```mermaid
sequenceDiagram
    autonumber
    participant User as Developer
    participant UI as Next.js Web App
    participant AuthAPI as Auth Domain
    participant DB as PostgreSQL (users, sessions)

    User->>UI: Enter Credentials (or OAuth)
    UI->>AuthAPI: POST /api/v1/auth/login
    AuthAPI->>DB: Lookup user & verify password hash
    DB-->>AuthAPI: User record (active, not deleted)
    AuthAPI->>DB: Create session record
    AuthAPI-->>UI: Set Secure HttpOnly Session Cookie
    UI-->>User: Redirect to Workspace Dashboard
```

---

### B. Grounded Chat & SSE Streaming Flow (Sprints 10–12)

```mermaid
sequenceDiagram
    autonumber
    participant User as Developer
    participant UI as Chat Interface
    participant ChatAPI as Chat Router
    participant Retrieval as RAG Engine
    participant Gateway as AI Gateway
    participant Provider as External LLM (e.g. Claude / GPT-4)
    participant DB as PostgreSQL

    User->>UI: Submit Message ("How does auth work?")
    UI->>ChatAPI: POST /api/v1/conversations/{id}/messages (Stream: true)
    ChatAPI->>DB: Persist user message
    ChatAPI->>Retrieval: Retrieve relevant chunks & symbols
    Retrieval->>DB: pgvector cosine similarity search
    DB-->>Retrieval: Relevant document chunks with citations
    Retrieval-->>ChatAPI: Context chunks & file references
    ChatAPI->>Gateway: Format prompt + untrusted context
    Gateway->>Provider: Request streaming completion
    Provider-->>Gateway: Token stream
    Gateway-->>ChatAPI: Token stream + citation events
    ChatAPI-->>UI: Server-Sent Events (SSE chunks)
    UI-->>User: Progressive render with line citations
    ChatAPI->>DB: Persist assistant message & token usage
```

---

### C. Human-Approved Agent Task Execution Flow (Sprints 19–21)

```mermaid
sequenceDiagram
    autonumber
    participant Dev as Developer
    participant UI as Task View
    participant Agent as Agent Orchestrator
    participant Sandbox as Execution Sandbox
    participant GitHub as GitHub API

    Dev->>UI: Request task ("Add test for health check")
    UI->>Agent: Plan generation request
    Agent->>Agent: Generate structured diff plan & compute SHA256 Plan Hash
    Agent-->>UI: Display plan, diff, and confirmation prompt
    Dev->>UI: Click "Approve Plan" (signing Plan Hash)
    UI->>Agent: POST /tasks/{id}/execute { approved_hash }
    Agent->>Agent: Verify approved_hash == planned_hash
    Agent->>Sandbox: Apply file edits & execute `uv run pytest`
    Sandbox-->>Agent: Test results: 90 passed, 0 failed
    Agent-->>UI: Display test output & prompt for PR creation
    Dev->>UI: Click "Create Draft Pull Request"
    UI->>Agent: POST /tasks/{id}/push
    Agent->>GitHub: Create branch, commit, and open Draft PR
    GitHub-->>Agent: Draft PR #42 Created
    Agent-->>UI: Display clickable Draft PR link
```
