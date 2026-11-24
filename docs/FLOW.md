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
    participant Redis as Redis (Session Cache)

    User->>UI: Enter Credentials (or OAuth)
    UI->>AuthAPI: POST /api/v1/auth/login
    AuthAPI->>DB: Lookup user & verify password hash (Argon2id)
    DB-->>AuthAPI: User record (active, not deleted)
    AuthAPI->>Redis: SET session:{token} (User context, TTL: 900s)
    AuthAPI-->>UI: Set-Cookie: kontexa_session={token} (HttpOnly, Secure, SameSite=Lax)
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
    ChatAPI-->>UI: Server-Sent Events (SSE chunks: token, citation, usage)
    UI-->>User: Progressive render with line citations
    ChatAPI->>DB: Persist assistant message & token usage
```

---

### C. Knowledge Ingestion & Sliding-Window Chunking Flow (Sprint 13)

```mermaid
sequenceDiagram
    autonumber
    participant Dev as Developer
    participant UI as Project Knowledge View
    participant API as Document API
    participant Queue as Redis Job Queue
    participant Worker as Background Worker
    participant Gateway as AI Gateway
    participant DB as PostgreSQL (pgvector)

    Dev->>UI: Upload architecture_rfc.md (Size <= 25MB)
    UI->>API: POST /api/v1/projects/{proj_id}/documents (Multipart Form)
    API->>API: Validate MIME type & file size
    API->>DB: INSERT INTO documents (name, path, mime_type)
    API->>Queue: Enqueue task: process_document(doc_id)
    API-->>UI: HTTP 202 Accepted { document_id, status: "queued" }

    Worker->>Queue: Dequeue process_document task
    Worker->>Worker: Compute content SHA-256 hash
    alt Content matches previous version hash
        Worker->>DB: Skip duplicate processing (status="current")
    else New content hash
        Worker->>Worker: Parse text & split into chunks (500 tokens / 50 overlap)
        Worker->>Gateway: Generate embeddings for text chunks (batch of 64)
        Gateway-->>Worker: List of 1536-dim float vectors
        Worker->>DB: INSERT INTO document_versions & document_chunks (with pgvector embedding)
        Worker->>DB: UPDATE documents SET status="ready"
    end
```

---

### D. Repository Synchronization & AST Symbol Indexing Flow (Sprints 15–16)

```mermaid
sequenceDiagram
    autonumber
    participant Admin as Workspace Admin
    participant UI as Connectors View
    participant API as Connectors API
    participant Queue as Redis Job Queue
    participant Worker as Background Worker
    participant GitHub as GitHub REST/GraphQL API
    participant DB as PostgreSQL

    Admin->>UI: Authorize GitHub App & select repo `org/repo`
    UI->>API: POST /api/v1/connectors/github/sync
    API->>Queue: Enqueue task: sync_repository(repo_id)
    API-->>UI: HTTP 202 Accepted { status: "sync_queued" }

    Worker->>Queue: Dequeue sync_repository task
    Worker->>GitHub: Fetch repository tree & commit log (since last SHA)
    GitHub-->>Worker: Git tree object & modified file blobs
    Worker->>Worker: Filter files respecting .gitignore
    Worker->>Worker: Parse AST for Python & TypeScript files (extract functions, classes, imports)
    Worker->>DB: Upsert repository files, AST symbols, and commit metadata
    Worker->>DB: Enqueue chunking & embedding for modified code files
```

---

### E. Human-Approved Agent Task Execution Flow (Sprints 19–21)

```mermaid
sequenceDiagram
    autonumber
    participant Dev as Developer
    participant UI as Task View
    participant Agent as Agent Orchestrator
    participant Sandbox as Execution Sandbox
    participant GitHub as GitHub API
    participant DB as PostgreSQL

    Dev->>UI: Request task ("Add test for health check")
    UI->>Agent: Plan generation request
    Agent->>Agent: Generate structured diff plan & compute SHA256 Plan Hash
    Agent->>DB: INSERT INTO agent_runs (status="awaiting_approval", plan_hash=plan_hash)
    Agent-->>UI: Display plan, diff, and confirmation prompt
    Dev->>UI: Click "Approve Plan" (signing Plan Hash)
    UI->>Agent: POST /tasks/{id}/execute { approved_plan_hash }
    Agent->>Agent: Assert approved_plan_hash == plan_hash
    Agent->>Sandbox: Apply file edits & execute `uv run pytest` (Timeout: 120s)
    Sandbox-->>Agent: Test results: 90 passed, 0 failed
    Agent-->>UI: Display test output & prompt for PR creation
    Dev->>UI: Click "Create Draft Pull Request"
    UI->>Agent: POST /tasks/{id}/push
    Agent->>GitHub: Create branch, commit, and open Draft PR
    GitHub-->>Agent: Draft PR #42 Created
    Agent->>DB: UPDATE agent_runs SET status="completed", pr_url="..."
    Agent-->>UI: Display clickable Draft PR link
```
