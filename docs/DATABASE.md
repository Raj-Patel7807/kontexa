# Executive Summary

Kontexa is a cloud-based SaaS platform for team collaboration with AI-assisted development tools. Its data model includes **multi-tenant workspaces/projects**, **user and conversation data**, **documents for retrieval-augmented generation (RAG)** (with vector embeddings), and **auditing/memory/tool-usage logs**. We propose a PostgreSQL schema that supports robust **multi-tenancy**, **pgvector integration**, and **enterprise-grade practices** (soft-deletes, UUID keys, timestamps, JSONB metadata, etc.). 

This design uses a *“pooled” multi-tenant model*, where each row has a `workspace_id` or `project_id` to identify its tenant. Row-Level Security (RLS) can be enabled later to enforce isolation at the database level. All tables use UUID primary keys (via `uuid_generate_v4()`) and `TIMESTAMPTZ` timestamps with sensible defaults. Vector embeddings (for documents, memory) use the `pgvector` extension (configured once via `CREATE EXTENSION vector;`). We will index text and JSONB fields with B-tree/GIN and vectors with HNSW/IVFFlat as appropriate.

The SQL DDL and Alembic migrations below show how to implement this schema. We also provide SQLAlchemy model examples (using `AsyncSession`) and recommended deployment options. **Modern managed Postgres providers (Railway, Neon, Supabase, Render, AWS RDS, etc.) all offer pgvector and features like high-availability and PITR.** We compare cost and features in tables. Finally, we cover backups, monitoring, security (e.g. TLS and rotated secrets), testing (Docker Compose + Pytest), and a step-by-step agent checklist. All guidance is up-to-date (2026) and sourced from official docs and experts.

---

## Database Design

### Multi-Tenancy Model

We use a **shared (“pool”) tenancy model**: all data lives in the same database, and every row includes a `workspace_id` (and/or `project_id`) foreign key. The application ensures filtering by workspace. Optionally, Row-Level Security (RLS) can be enabled on each table (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY`) so that only the owning tenant can see or modify its rows. RLS centralizes isolation enforcement in the database and eliminates reliance on application logic for each query.

> **Row-Level Security (RLS):** By enabling RLS policies on tables, the DB can automatically restrict rows to the current tenant (e.g. `WHERE workspace_id = current_setting('app.current_workspace')::UUID`). This reduces cross-tenant leakage risk. RLS is optional but recommended for production SaaS.

All tables reference a `workspaces` (tenant) table. Key approaches:
- **Pool model:** one database, one schema, add `workspace_id` to every table. Lower cost than separate DB per tenant.
- **Schema-per-tenant:** not used here, too complex for dynamic tenants.
- **DB-per-tenant:** too expensive for many teams (we keep a single DB).

We require each row’s `workspace_id` (and `project_id` if relevant) to maintain tenant boundaries. In some tables, there’s also a `user_id` to link to the owning user (for user-created content, sessions, etc.).

### Entity-Relationship Diagram

Below is a simplified ER diagram (Mermaid) of the core tables.  Each table’s name is followed by its key columns.  Lines indicate foreign keys.

```mermaid
erDiagram
    USERS ||--o{ WORKSPACES : owns
    USERS ||--o{ WORKSPACE_MEMBERS : 
    WORKSPACES ||--o{ WORKSPACE_MEMBERS : 
    WORKSPACES ||--o{ PROJECTS : 
    WORKSPACE_MEMBERS ||--|| USERS : 
    WORKSPACE_MEMBERS ||--|| WORKSPACES : 
    PROJECTS ||--o{ CONVERSATIONS : 
    PROJECTS ||--o{ DOCUMENTS : 
    CONVERSATIONS ||--o{ MESSAGES : 
    MESSAGES ||--o{ MESSAGE_PARTS : 
    DOCUMENTS ||--o{ DOCUMENT_VERSIONS : 
    DOCUMENT_VERSIONS ||--o{ DOCUMENT_CHUNKS : 
    DOCUMENT_CHUNKS ||--o{ MEMORY_ENTRIES : 
    PROJECTS ||--o{ TASKS : 
    PROJECTS ||--o{ TOOL_EXECUTIONS : 
    CONVERSATIONS ||--o{ TOOL_EXECUTIONS : 
    USERS ||--o{ OAUTH_ACCOUNTS : 
    WORKSPACES ||--o{ INTEGRATIONS : 
    INTEGRATIONS ||--o{ DOCUMENTS : 
    PROJECTS ||--o{ GITHUB_CONNECTIONS : 
    GITHUB_CONNECTIONS ||--o{ GITHUB_REPOSITORIES : 
    GITHUB_REPOSITORIES ||--o{ GITHUB_COMMITS : 
    GITHUB_REPOSITORIES ||--o{ GITHUB_PULL_REQUESTS : 
    PROJECTS ||--o{ AUDIT_LOGS : 
    WORKSPACES ||--o{ AUDIT_LOGS : 
    USERS ||--o{ AUDIT_LOGS : 
```

**Key entities:** 

- **workspaces:** Tenant or team container.  
- **users:** Application users (joined to workspaces via `workspace_members`).  
- **projects:** Projects within workspaces.  
- **conversations, messages, message_parts:** Chat history (threaded).  
- **documents/document_versions/chunks:** RAG content from GitHub/Uploads, etc., broken into chunks with embeddings.  
- **memory_entries:** Stored embeddings/memories (semantic/episodic).  
- **tools/tool_executions:** Records of agent/tool actions.  
- **audit_logs:** System events.  
- **oauth_accounts/github_*:** (Optional) integration credentials and GitHub data for connected repos.

Each table includes `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`, `updated_at TIMESTAMPTZ`, and often a `deleted_at TIMESTAMPTZ` for soft-deletes. UUIDs (`uuid` type) are used for IDs, defaulting to `uuid_generate_v4()`.

### Table Schema (logical)

Below is the **logical schema** summary. For brevity we list each table with columns and constraints. All `id` columns are `UUID PRIMARY KEY DEFAULT uuid_generate_v4()`. `created_at`/`updated_at` are `TIMESTAMPTZ DEFAULT now()`. Foreign keys reference parent tables with `ON DELETE CASCADE` or `RESTRICT` as noted.

- **users**: Authentication data.  
  - `id UUID PK`  
  - `email TEXT UNIQUE NOT NULL`, `password_hash TEXT`, `name TEXT`, `avatar_url TEXT`,  
  - `is_active BOOLEAN DEFAULT true`, `is_verified BOOLEAN DEFAULT false`,  
  - `last_login_at TIMESTAMPTZ`, `created_at`, `updated_at`.  
  - *(Consider encryption for `password_hash` and `access tokens` – see Security.)*

- **workspaces**: Team/tenant.  
  - `id UUID PK`  
  - `owner_id UUID REFERENCES users(id) ON DELETE SET NULL`,  
  - `name TEXT NOT NULL`, `slug TEXT UNIQUE NOT NULL`, `description TEXT`,  
  - `created_at`, `updated_at`.

- **workspace_members**: M2M linking users to workspaces.  
  - `id UUID PK`  
  - `workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE`,  
  - `user_id UUID REFERENCES users(id) ON DELETE CASCADE`,  
  - `role TEXT NOT NULL CHECK(role IN ('owner','admin','member','viewer'))`,  
  - `created_at`, `updated_at`.  
  - *Index:* unique `(workspace_id, user_id)`.

- **projects**: Projects within workspaces.  
  - `id UUID PK`  
  - `workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE`,  
  - `name TEXT NOT NULL`, `slug TEXT NOT NULL`, `description TEXT`, `status TEXT`,  
  - `created_at`, `updated_at`.  
  - *Constraints:* Unique `(workspace_id, slug)`; index on `workspace_id`.

- **conversations**: Chat threads (within a project).  
  - `id UUID PK`  
  - `project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE`,  
  - `user_id UUID REFERENCES users(id)`, (who started it)  
  - `title TEXT`, `status TEXT`,  
  - `created_at`, `updated_at`, `archived_at TIMESTAMPTZ`.  
  - *Index:* `(project_id, created_at)`.

- **messages**: Chat messages in a conversation.  
  - `id UUID PK`  
  - `conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE`,  
  - `role TEXT NOT NULL CHECK (role IN ('user','assistant','system','tool'))`,  
  - `content TEXT`, (raw text content)  
  - `model TEXT`, (e.g. which LLM generated it)  
  - `created_at TIMESTAMPTZ DEFAULT now()`.

- **message_parts**: Decomposed message content (for structured response).  
  - `id UUID PK`  
  - `message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE`,  
  - `part_type TEXT NOT NULL`, (e.g. 'text', 'code', 'citation', 'image', etc.)  
  - `content JSONB NOT NULL`, (structured content)  
  - `sequence INTEGER NOT NULL`,  
  - `created_at TIMESTAMPTZ DEFAULT now()`.  
  - *Index:* `(message_id, sequence)` to preserve order.

- **documents**: User-uploaded or integrated docs (for RAG).  
  - `id UUID PK`  
  - `project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE`,  
  - `name TEXT NOT NULL`, `source_type TEXT`, `source_url TEXT`, `mime_type TEXT`,  
  - `size_bytes BIGINT`, `checksum TEXT`,  
  - `status TEXT`, `metadata JSONB`,  
  - `created_at`, `updated_at`.  
  - Example `source_type` values: 'upload','github','notion','slack','jira', etc.

- **document_versions**: Version history (e.g. for GitHub files or updated docs).  
  - `id UUID PK`  
  - `document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE`,  
  - `version_number INTEGER NOT NULL`, `checksum TEXT`, `content_hash TEXT`,  
  - `metadata JSONB`,  
  - `created_at TIMESTAMPTZ DEFAULT now()`.  
  - *Index:* `(document_id, version_number)`.

- **document_chunks**: Chunks of a document version (for embeddings).  
  - `id UUID PK`  
  - `document_version_id UUID NOT NULL REFERENCES document_versions(id) ON DELETE CASCADE`,  
  - `chunk_index INTEGER NOT NULL`, `content TEXT NOT NULL`, `token_count INTEGER`,  
  - `metadata JSONB`,  
  - `embedding VECTOR(\\<dim>)`, *(replace \\<dim> with chosen dimension, e.g. 1536)*  
  - `created_at TIMESTAMPTZ DEFAULT now()`.  
  - *Index:* `(document_version_id, chunk_index)`.  
  - *Vector Index:* e.g. `CREATE INDEX ON document_chunks USING hnsw (embedding vector_l2_ops)` after populating data.

- **memory_entries**: Persistent memory/embedding store.  
  - `id UUID PK`  
  - `project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE`,  
  - `user_id UUID REFERENCES users(id)`, (optional owner or null for system memory)  
  - `memory_type TEXT NOT NULL CHECK (memory_type IN ('semantic','episodic','procedural'))`,  
  - `content TEXT NOT NULL`, `metadata JSONB`, `importance REAL`,  
  - `embedding VECTOR(\\<dim>)`,  
  - `created_at`, `updated_at`, `expires_at TIMESTAMPTZ`.  
  - *Index:* `(project_id)`; vector index on `embedding`.

- **oauth_accounts**: External auth (GitHub, Google, etc.).  
  - `id UUID PK`  
  - `user_id UUID REFERENCES users(id) ON DELETE CASCADE`,  
  - `provider TEXT NOT NULL`, `provider_account_id TEXT NOT NULL`,  
  - `access_token TEXT`, `refresh_token TEXT`, `expires_at TIMESTAMPTZ`,  
  - `created_at`, `updated_at`.  

- **github_connections**: Stored GitHub credentials (if separate from oauth).  
  - `id UUID PK`  
  - `user_id UUID REFERENCES users(id) ON DELETE CASCADE`,  
  - `provider_account_id TEXT`, `access_token TEXT`, `refresh_token TEXT`, `expires_at TIMESTAMPTZ`,  
  - `created_at`, `updated_at`.  

- **github_repositories**: GitHub repos synced or connected.  
  - `id UUID PK`  
  - `project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE`,  
  - `connection_id UUID NOT NULL REFERENCES github_connections(id) ON DELETE CASCADE`,  
  - `github_id BIGINT`, `owner_name TEXT`, `repo_name TEXT`, `full_name TEXT`,  
  - `default_branch TEXT`, `url TEXT`, `is_private BOOLEAN`,  
  - `last_synced_at TIMESTAMPTZ`, `created_at`, `updated_at`.  

- **github_commits**: Commits fetched for RAG or auditing.  
  - `id UUID PK`  
  - `repository_id UUID NOT NULL REFERENCES github_repositories(id) ON DELETE CASCADE`,  
  - `github_id TEXT`, `sha TEXT`, `message TEXT`,  
  - `author_name TEXT`, `author_email TEXT`, `committed_at TIMESTAMPTZ`, `url TEXT`,  
  - `metadata JSONB`, `created_at TIMESTAMPTZ DEFAULT now()`.  

- **github_pull_requests**, **github_issues**, etc.: Similar structure (id, repo ref, number, title/body, state, author, timestamps).  

- **repository_files** (optional): To index code files.  
  - `id UUID PK`  
  - `repository_id UUID NOT NULL REFERENCES github_repositories(id) ON DELETE CASCADE`,  
  - `path TEXT`, `branch TEXT`, `sha TEXT`, `language TEXT`, `size_bytes BIGINT`, `content_hash TEXT`,  
  - `document_id UUID NULL REFERENCES documents(id)`, (if it’s linked to a document entry)  
  - `created_at`, `updated_at`.  

- **tools**: AI tool definitions.  
  - `id UUID PK`  
  - `name TEXT UNIQUE NOT NULL`, `description TEXT`, `tool_type TEXT`,  
  - `input_schema JSONB`, `output_schema JSONB`, `is_active BOOLEAN DEFAULT true`,  
  - `created_at`, `updated_at`.  

- **tool_executions**: History of tool (Act) invocations.  
  - `id UUID PK`  
  - `project_id UUID NOT NULL REFERENCES projects(id)`,  
  - `conversation_id UUID REFERENCES conversations(id)`, `message_id UUID REFERENCES messages(id)`,  
  - `tool_id UUID NOT NULL REFERENCES tools(id)`,  
  - `status TEXT`, `input JSONB`, `output JSONB`, `error TEXT`,  
  - `started_at TIMESTAMPTZ DEFAULT now()`, `completed_at TIMESTAMPTZ`, `duration_ms INTEGER`.  

- **agent_runs** / **agent_steps**: (Future feature, tracks multi-step agent execution.)  
  - `agent_runs(id PK, project_id, conversation_id, status, agent_type, input JSONB, output JSONB, timestamps)`.  
  - `agent_steps(id PK, agent_run_id FK, step_number INTEGER, step_type TEXT, input/output JSONB, status, timestamps)`.  

- **tasks**: To-do items.  
  - `id UUID PK`  
  - `project_id UUID NOT NULL REFERENCES projects(id)`,  
  - `created_by UUID REFERENCES users(id)`, `conversation_id UUID REFERENCES conversations(id)`,  
  - `title TEXT NOT NULL`, `description TEXT`,  
  - `status TEXT`, `priority TEXT`, `due_at TIMESTAMPTZ`,  
  - `created_at`, `updated_at`, `completed_at TIMESTAMPTZ`.  

- **audit_logs**: Record system events.  
  - `id UUID PK`  
  - `workspace_id UUID REFERENCES workspaces(id)`, `project_id UUID REFERENCES projects(id)`, `user_id UUID REFERENCES users(id)`,  
  - `action TEXT`, `resource_type TEXT`, `resource_id UUID`, `status TEXT`,  
  - `metadata JSONB`, `ip_address INET`,  
  - `created_at TIMESTAMPTZ DEFAULT now()`.  

- **llm_providers** / **llm_models** / **llm_usage**:  
  - *llm_providers:* `id, name, provider_type, is_active, created_at, updated_at`.  
  - *llm_models:* `id, provider_id FK, model_name, context_window, supports_streaming, supports_tools, is_active, created_at`.  
  - *llm_usage:* tracks tokens/cost per message (user_id, project_id, conversation_id, message_id, model_id, input_tokens, output_tokens, total_tokens, latency_ms, estimated_cost, created_at).  

- **policies / policy_events**: For later guardrails.  
  - *policies:* `id, workspace_id, name, policy_type, rules JSONB, is_active, created_at, updated_at`.  
  - *policy_events:* `id, policy_id FK, project_id, user_id, action, decision, reason, metadata JSONB, created_at`.  

### Indexing and Extensions

- **UUID and Timestamps:** Use `uuid` with `uuid_generate_v4()` (from the `uuid-ossp` extension) as `DEFAULT`. Timestamp columns `created_at`, `updated_at` use `TIMESTAMPTZ DEFAULT now()`.  
- **Primary & Foreign Keys:** All PKs are UUID. FKs should be indexed automatically, but we also create explicit indexes on foreign keys (e.g. `CREATE INDEX ON messages(conversation_id)`), plus on commonly filtered columns (`projects(workspace_id)`, `memory_entries(project_id)`, etc.).  
- **Soft-delete:** Add a `deleted_at TIMESTAMPTZ NULL` or `is_deleted BOOLEAN` on tables where records might be soft-deleted (e.g. `conversations.deleted_at`). Use partial indexes to exclude deleted rows if needed (e.g. `WHERE deleted_at IS NULL`).  
- **JSONB:** Several tables have JSONB (`metadata` fields in documents, commits, audit_logs, tools, etc.). For large metadata searches, add GIN indexes. For example:  
  ```sql
  CREATE INDEX idx_documents_metadata ON documents USING GIN (metadata);
  ```  
  As the Postgres manual notes, GIN indexes on `jsonb` greatly speed up `@>` containment queries. For arrays or text search within JSON, consider `jsonb_path_ops`.  
- **Full-Text:** You may also use `tsvector` columns or `GIN` on `(to_tsvector('english', column))` for any text search fields (chat logs, tasks, etc.), though often simple `ILIKE` or specialized search tools (ElasticSearch) are used in RAG systems.

- **Vectors (pgvector):** Enable `CREATE EXTENSION IF NOT EXISTS vector;` once per database. Define vector columns (e.g. `VECTOR(1536)` if using OpenAI 1536-dim embeddings).  
  - **Indexing vectors:** Use approximate NN indexes for performance. Examples: 
    ```sql
    -- L2 distance index
    CREATE INDEX idx_chunks_embedding ON document_chunks USING hnsw (embedding vector_l2_ops);
    -- Cosine distance index (if vectors are normalized)
    CREATE INDEX idx_chunks_embedding_cos ON document_chunks USING hnsw (embedding vector_cosine_ops);
    ``` 
    Use `ivfflat` if you want more control: 
    ```sql
    CREATE INDEX idx_mem_ivf ON memory_entries USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);
    ``` 
  - **Distance operators:** Use `<->` for L2, `<#>` for inner-product, `<=>` for cosine.  
  - **Vacuum Hint:** After bulk-loading vectors, create indexes `CONCURRENTLY` to avoid locking.

### Partitioning and Scaling

For very large tables (e.g. `messages`, `document_chunks`, `memory_entries`), consider:

- **Partitioning:** PostgreSQL supports declarative table partitioning (e.g. by date or by workspace). For example, partition `messages` by range of `created_at`, or `conversation_id`. This can improve query performance and maintenance (VACUUM on partitions). Another option is manual sharding (e.g. Citus) for multi-region scale. 
- **Replicas:** Use read replicas for analytics or heavy read/query loads, as offered by cloud providers.
- **Connection Pooling:** The application should use a pool (PgBouncer, SQLAlchemy pool) since cloud DB connections are limited. As noted, lack of pooling will exhaust `max_connections` quickly.

### Audit and Soft-Delete

- Each table has `created_at`/`updated_at`. For audit, either use `audit_logs` or enable **`pgaudit`** extension to log SQL changes. 
- Soft-delete: Optionally add `deleted_at TIMESTAMPTZ` on mutable tables. Use queries like `WHERE deleted_at IS NULL` or policies to ignore them. 

### Sample CREATE TABLE (logical DDL)

```sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Users
CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    name          TEXT,
    avatar_url    TEXT,
    is_active     BOOLEAN NOT NULL DEFAULT true,
    is_verified   BOOLEAN NOT NULL DEFAULT false,
    last_login_at TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Workspaces
CREATE TABLE workspaces (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id    UUID REFERENCES users(id) ON DELETE SET NULL,
    name        TEXT NOT NULL,
    slug        TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Workspace Members
CREATE TABLE workspace_members (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role         TEXT NOT NULL CHECK (role IN ('owner','admin','member','viewer')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (workspace_id, user_id)
);

-- Projects
CREATE TABLE projects (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id  UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    slug          TEXT NOT NULL,
    description   TEXT,
    status        TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(workspace_id, slug)
);

-- Conversations (Chat)
CREATE TABLE conversations (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id     UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id        UUID REFERENCES users(id),
    title          TEXT,
    status         TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    archived_at    TIMESTAMPTZ
);

-- Messages
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('user','assistant','system','tool')),
    content         TEXT NOT NULL,
    model           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Message Parts (for structured segments)
CREATE TABLE message_parts (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id  UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    part_type   TEXT NOT NULL,
    content     JSONB NOT NULL,
    sequence    INTEGER NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (message_id, sequence)
);

-- Documents
CREATE TABLE documents (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id     UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name           TEXT NOT NULL,
    source_type    TEXT,
    source_url     TEXT,
    mime_type      TEXT,
    size_bytes     BIGINT,
    checksum       TEXT,
    status         TEXT,
    metadata       JSONB,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Document Versions
CREATE TABLE document_versions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version_number  INTEGER NOT NULL,
    checksum        TEXT,
    content_hash    TEXT,
    metadata        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (document_id, version_number)
);

-- Document Chunks (with vector)
CREATE TABLE document_chunks (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_version_id UUID NOT NULL REFERENCES document_versions(id) ON DELETE CASCADE,
    chunk_index         INTEGER NOT NULL,
    content             TEXT NOT NULL,
    token_count         INTEGER,
    metadata            JSONB,
    embedding           VECTOR(1536),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (document_version_id, chunk_index)
);

-- Memory Entries
CREATE TABLE memory_entries (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id   UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id      UUID REFERENCES users(id),
    memory_type  TEXT NOT NULL CHECK (memory_type IN ('semantic','episodic','procedural')),
    content      TEXT NOT NULL,
    metadata     JSONB,
    importance   REAL,
    embedding    VECTOR(1536),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at   TIMESTAMPTZ
);

-- Tool Executions
CREATE TABLE tool_executions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id),
    message_id      UUID REFERENCES messages(id),
    tool_id         UUID NOT NULL REFERENCES tools(id),
    status          TEXT,
    input           JSONB NOT NULL,
    output          JSONB,
    error           TEXT,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ,
    duration_ms     INTEGER
);

-- Audit Logs
CREATE TABLE audit_logs (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id  UUID REFERENCES workspaces(id),
    project_id    UUID REFERENCES projects(id),
    user_id       UUID REFERENCES users(id),
    action        TEXT NOT NULL,
    resource_type TEXT,
    resource_id   UUID,
    status        TEXT,
    metadata      JSONB,
    ip_address    INET,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- (Additional tables like tools, agent_runs, tasks, oauth_accounts, GitHub repos/commits, etc. follow similar patterns.)
```

**Notes on indexes:** Add indexes on foreign keys and frequently filtered fields. Example:  
```sql
CREATE INDEX ON messages(conversation_id);
CREATE INDEX ON document_chunks(document_version_id);
CREATE INDEX ON memory_entries(project_id);
-- GIN index on JSONB:
CREATE INDEX ON documents USING GIN (metadata jsonb_path_ops);
-- Full-text search:
CREATE INDEX ON messages USING GIN (to_tsvector('english', content));
```
GIN indexes on `jsonb` allow `@>` and existence (`?`) queries.

**Vector indexing example:**  
```sql
-- Approximate search index for L2 distance
CREATE INDEX idx_chunks_embedding_hnsw ON document_chunks USING hnsw (embedding vector_l2_ops);
``` 
(as recommended by pgvector docs).

### Partitioning / Sharding

For very large tables (messages, chunks, memory), consider partitioning by `created_at` or `workspace_id`. Partitioning can speed up deletion of old data and reduce vacuuming scope. If global scale is needed, PostgreSQL supports logical sharding (e.g. Citus), but that is advanced. Initially, a single well-provisioned instance with proper indexing and connection pooling should suffice.

---

## DDL Scripts

Below is a **production-ready DDL script outline**. Include necessary extensions, roles, and schema. In a real setup, grant minimal privileges to the app user, not superuser. 

```sql
-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Roles (example)
CREATE ROLE app_user NOINHERIT LOGIN PASSWORD '<secure_pwd>';
GRANT CONNECT ON DATABASE Kontexa_db TO app_user;

-- Schemas (if needed; default "public" is fine)
CREATE SCHEMA IF NOT EXISTS Kontexa AUTHORIZATION app_user;

-- Switch to that schema
SET search_path = Kontexa, public;

-- (Then CREATE TABLEs as above, using the schema.)
-- For brevity, assume tables above are created under `Kontexa.` schema.

-- Example Indexes
CREATE INDEX idx_messages_conversation ON Kontexa.messages(conversation_id);
CREATE INDEX idx_projects_workspace ON Kontexa.projects(workspace_id);
CREATE INDEX idx_mem_proj ON Kontexa.memory_entries(project_id);

-- pgvector Index (approximate nearest neighbor)
CREATE INDEX idx_chunks_embedding_hnsw 
  ON Kontexa.document_chunks USING hnsw (embedding vector_l2_ops);

-- JSONB/Gin indexes
CREATE INDEX idx_docs_metadata_gin ON Kontexa.documents USING GIN (metadata jsonb_path_ops);
CREATE INDEX idx_audit_metadata_gin ON Kontexa.audit_logs USING GIN (metadata);

-- (Add any additional indexes needed for queries, e.g. on `workspace_members` (workspace_id, user_id), etc.)
```

For **reading vs writing** optimization, you might later create indexes with `CONCURRENTLY` to avoid locks. Also consider `BRIN` indexes on large date columns if historical data access is common.

---

## Alembic Migration Plan

We will use Alembic for migrations. Below is the suggested **ordered list of migration files** and their main content:

1. **`001_initial.py`** – Create foundational tables:
   - `users`, `workspaces`, `workspace_members`, `projects`.
   - Possibly `oauth_accounts` if included from the start.
   - Enable `uuid-ossp` extension and set up any enum types or check constraints.
2. **`002_auth_sessions.py`** – Add tables for auth/session:
   - `user_sessions` (if using JWT refresh tokens, etc).
   - `oauth_accounts` (if not in initial).
3. **`003_chat.py`** – Add messaging:
   - `conversations`, `messages`, `message_parts`.
4. **`004_tools_and_agency.py`** – Tools/Agents:
   - `tools`, `tool_executions`, `agent_runs`, `agent_steps`.
5. **`005_documents_rag.py`** – RAG content:
   - `documents`, `document_versions`, `document_chunks`, `message_citations`.
   - Enable `vector` extension.
6. **`006_memory.py`** – Memory:
   - `memory_entries` table.
7. **`007_integrations.py`** – External integrations:
   - `github_connections`, `github_repositories`, (optionally Slack, Notion later).
8. **`008_github_data.py`** – GitHub content:
   - `github_commits`, `github_pull_requests`, `github_issues`, `repository_files`.
9. **`009_tasks_audit.py`** – Tasks and auditing:
   - `tasks`, `audit_logs`.
10. **`010_policies.py`** – (Future) Guardrails:
    - `policies`, `policy_events`.

Each migration will include `op.create_table` calls and any `op.create_index` or `op.add_column` as needed. For example, in Alembic script:

```python
def upgrade():
    # Enable extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    op.execute('CREATE EXTENSION IF NOT EXISTS vector;')
    # Create tables
    op.create_table('users', ...)
    op.create_table('workspaces', ...)
    ...
    # Create indexes
    op.create_index('ix_projects_workspace', 'projects', ['workspace_id'])
```

Always include `downgrade()` stubs if needed (for rollbacks). Keep migrations small and incremental to ease review. See the [Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html) for details on environment setup and script structure.

---

## SQLAlchemy (Async) Models

Below are **example SQLAlchemy ORM models** (using the `asyncio` extension). Adjust for your project’s organization. We assume usage of `sqlalchemy.ext.asyncio` and declarative base.

```python
# models.py
from sqlalchemy import Column, String, ForeignKey, Text, TIMESTAMP, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET, REAL, VECTOR
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(Text)
    name = Column(String)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    # ...

class Workspace(Base):
    __tablename__ = 'workspaces'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    # Relationships
    owner = relationship("User", back_populates="owned_workspaces")
    members = relationship("WorkspaceMember", back_populates="workspace")

class WorkspaceMember(Base):
    __tablename__ = 'workspace_members'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    __table_args__ = (
        UniqueConstraint('workspace_id', 'user_id', name='uq_workspace_user'),
    )
    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User", back_populates="memberships")

# Define other models similarly...
```

```python
# engine_setup.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://<user>:<password>@<host>:5432/Kontexa_db"

# Create async engine
async_engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # or False
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine, expire_on_commit=False
)

# Example of getting a session:
# async with AsyncSessionLocal() as session:
#     async with session.begin():
#         session.add(some_object)
```

This follows SQLAlchemy 2.0 style with `asyncio`. In an async context you run queries like `result = await session.execute(...)`. We set `expire_on_commit=False` so we can use objects after commit. See the [SQLAlchemy asyncio docs](https://docs.sqlalchemy.org/en/21/orm/extensions/asyncio.html) for patterns.

---

## Deployment and Hosting

**Frontend:** Deploy the Next.js app on Vercel (Vercel has a generous free tier for open-source projects).

**Backend:** For FastAPI, consider one of: **Railway**, **Render**, **Fly.io**, **Cloud Run**, or a small **VM (e.g. AWS Lightsail/GCP Compute)**. Many offer free or low-cost tiers:

- **Railway:** Easy Docker deploy, has managed Postgres & Redis. (Free with $1/mo credit; Hobby $5+.) Railway now provides HA Postgres with pgvector, PITR, built-in PgBouncer.
- **Render:** Similar PaaS (Heroku-like). Managed Postgres with PITR on paid plans, autoscaling storage. Basic Postgres ~\$6/mo.
- **Fly.io:** Can run both web and PostgreSQL (via Fly Postgres). Has a free tier (3 shared CPUs, 3GB RAM).
- **Google Cloud Run:** Can run the API. Use **Cloud SQL** for Postgres (no Always Free for Cloud SQL, only trial credits).
- **AWS:** EC2 or ECS for FastAPI; use **RDS/Aurora** for PostgreSQL. Note: AWS/Azure charges by hour. AWS free-tier micro is short-term (12mo).
- **Neon/Postgres-as-a-Service:** Neon has a **free tier** (serverless Postgres with pgvector). Supabase also has free (~500MB DB + pgvector). These are dedicated DB with best features (branching, etc.). 

**Database (Postgres):** We recommend a managed Postgres that supports pgvector (most do in 2026). Table comparing options:

| Provider      | Type             | Free Tier         | pgvector | PITR  | HA Failover | Observability | Notes                 |
|---------------|------------------|-------------------|----------|-------|-------------|---------------|-----------------------|
| **Railway**   | PaaS (integrated)| $1/mo credit Free | ✔️       | ✔️   | ✔️ (Patroni) | ✅ Metrics    | Private networking, usage-based pricing |
| **Neon**      | Dedicated SaaS   | Generous free     | ✔️       | ✔️   | auto-scaling| ✅            | Branching, scale-to-zero |
| **Supabase**  | Dedicated BaaS   | Free (500MB)      | ✔️       | ✔️ (paid)| ✖️       | ✅            | Built-in auth/storage, easy pgvector |
| **Render**    | PaaS (Heroku-like)| Free trial ($7)  | ✔️       | ✔️(paid) | ✖️ (single)  | ✅            | Basic \$6/mo plans; private networking to services |
| **Heroku**    | PaaS             | *No free now*    | ✔️(standard+) | ✔️ | ✖️         | ✅            | New standard plans include pgvector (not free) |
| **AWS RDS/Aurora** | Hyperscaler  | N/A (Trial $)    | ✔️ (via extension)| ✔️| ✔️         | ✅ CloudWatch| Enterprise-grade SLAs, but cross-AZ latency potential |
| **Google Cloud SQL** | Hyperscaler | No always-free   | ✔️| ✔️| ✔️         | ✅ Stackdriver| Similar to AWS, high reliability |
| **Fly.io**    | PaaS             | Free tier         | ✔️ (fly-postgres)| ✖️ | ✔️ (leader) | ✅            | Deploy DB as separate HA cluster within Fly |
| **DigitalOcean/DO** | IaaS + Managed | 1GB Free (referral) | ✔️ | ✔️ | ✖️ (single) | ✅ DO metrics  | Managed Postgres \$9/mo minimum |

*Sources:* Most providers now include pgvector support and advanced features out-of-box. Choose a provider that keeps your app and DB in the same region/network (to reduce latency/cost).

**Redis:** Use for cache/session. Options:
- If on Railway/Render, use their managed Redis add-on (some free credits available).
- **Upstash**: Free tier (30MB) for simple rate-limiting or token bucket.
- **AWS Elasticache**: not free (no free tier beyond trial).
- Or run Redis in a Docker container (Docker Compose locally, or as a service/sidecar in production).
  
**Secrets Management:** Store DB and API credentials as environment variables in your deployment platform (Railway, Render, Vercel env). Use tools like [Vault](https://www.vaultproject.io) or provider secrets (AWS Secrets Manager, etc) for production. Do **not** hardcode secrets.

**Connection Strings:** Example for SQLAlchemy/Async: 
```env
DATABASE_URL=postgresql+asyncpg://app_user:<password>@<host>:5432/Kontexa_db
REDIS_URL=redis://:<password>@<host>:6379/0
```

**High Availability:** In production, use providers with **automatic failover** and **point-in-time recovery (PITR)**. Railway, Neon, Supabase, AWS RDS, etc., support PITR and replicas. Plan nightly base backups plus continuous WAL archiving.

---

## Operational Considerations

- **Backups:** Regularly back up the database. Example commands (from official docs):
  ```bash
  # Logical backup (custom format) with pg_dump
  pg_dump -h <host> -U app_user -Fc Kontexa_db > Kontexa_db.dump

  # Restore:
  createdb Kontexa_db_new
  pg_restore -h <host> -U app_user -d Kontexa_db_new Kontexa_db.dump
  ```
  Use `-j` to parallelize restore if large. For textual dumps: `psql -d dbname < dumpfile`. Test restores regularly to ensure backups are valid.

- **Vacuum & Analyze:** Set `autovacuum` on (default) to clean up dead rows. You can manually run:
  ```sql
  VACUUM (ANALYZE) Kontexa.messages;
  ```
  As docs state, `VACUUM` reclaims space from deleted/updated rows. Running `VACUUM ANALYZE` keeps planner stats up-to-date. For HNSW indexes, occasionally `REINDEX CONCURRENTLY` if performance degrades.

- **Monitoring:** Use built-in Postgres stats:
  - `pg_stat_activity` for connections.
  - `pg_stat_statements` extension for query analysis.
  - Provider metrics (CPU, I/O, connections, replication lag).
  - Log slow queries (`log_min_duration_statement`). 
  - For pgvector: monitor recall vs index size (pgvector suggests comparing exact vs approximate search).
  - Consider tools like **pgAdmin**, **Datadog**, or **Sentry** for alerts.

- **Security Best Practices:**  
  - Use **TLS/SSL** for DB connections. Require SSL in Postgres by `ALTER SYSTEM SET ssl = on;`. Cloud DB services often enforce this by default.  
  - Store secrets in env vars or a vault, not in code. Rotate keys/tokens regularly.  
  - Use least-privilege DB roles: give the app user only necessary permissions.  
  - **Encryption at rest**: Managed DB services (AWS RDS, GCP, Neon) encrypt storage by default. For self-managed, consider Linux LUKS or filesystem encryption.  
  - **Audit logging**: Enable `pgaudit` if available to log table changes. Use the `audit_logs` table for application-level events (login, data import, etc.).  
  - **Network security**: Restrict DB access to your app’s IP or VPC. Avoid public accessibility if not needed. Use VPC peering or private networking (Railway/Render do this by default).

- **Maintenance:** Plan for minor updates and major version upgrades. Use blue-green deployments or replicas for zero-downtime. Test upgrades on a staging database first.

---

## Testing and CI

- **Local Development:** Use **Docker Compose** to run Postgres (with pgvector) and Redis locally. Example `docker-compose.yml`:
  ```yaml
  version: '3.8'
  services:
    postgres:
      image: postgres:15
      environment:
        - POSTGRES_DB=Kontexa_db
        - POSTGRES_USER=app_user
        - POSTGRES_PASSWORD=changeme
      ports:
        - "5432:5432"
      command: ["postgres", "-c", "shared_preload_libraries=vector"]
    redis:
      image: redis:7
      ports:
        - "6379:6379"
    backend:
      build: ./backend
      env_file: .env.local
      depends_on:
        - postgres
        - redis
    frontend:
      build: ./frontend
      ports:
        - "3000:3000"
  ```
  Ensure `shared_preload_libraries=vector` or run `psql -c "CREATE EXTENSION vector;"` on startup. Use `pytest-asyncio` for DB tests.

- **Unit/Integration Tests:** Use **pytest** with fixtures to create a temporary test database. Example fixture:
  ```python
  @pytest.fixture(scope="session")
  async def db_engine():
      engine = create_async_engine("postgresql+asyncpg://app_user:changeme@localhost:5432/test_db")
      async with engine.begin() as conn:
          await conn.run_sync(Base.metadata.create_all)
      yield engine
      # teardown
      async with engine.begin() as conn:
          await conn.run_sync(Base.metadata.drop_all)
      await engine.dispose()
  ```
  Use `async_sessionmaker` to get `AsyncSession` in tests. Populate with test data and assert queries.

- **CI (GitHub Actions):** In your workflow, spin up services:
  ```yaml
  jobs:
    test:
      runs-on: ubuntu-latest
      services:
        postgres:
          image: postgres:15
          env:
            POSTGRES_DB: test_db
            POSTGRES_USER: app_user
            POSTGRES_PASSWORD: changeme
          ports: ['5432:5432']
          options: >-
            --health-cmd pg_isready
            --health-interval 10s
            --health-timeout 5s
            --health-retries 5
        redis:
          image: redis:7
          ports: ['6379:6379']
      steps:
        - uses: actions/checkout@v3
        - name: Set up Python
          uses: actions/setup-python@v4
          with: python-version: '3.11'
        - name: Install dependencies
          run: pip install -r backend/requirements.txt
        - name: Run migrations
          run: alembic upgrade head
          env:
            DATABASE_URL: postgresql+asyncpg://app_user:changeme@localhost:5432/test_db
        - name: Run tests
          run: pytest --maxfail=1 --disable-warnings -v
  ```
  This ensures migrations run on a fresh DB and tests cover the DB models.

- **Linting/Formatting:** Use `ruff` and `black` (as per repo foundation) to enforce style. Add a pre-commit hook.

---

## Agent Implementation Tasks

The following **step-by-step instructions** can guide an AI agent (or developer) to implement the database integration:

1. **Switch branch:** Create and switch to a docs branch, e.g. `docs/Kontexa-roadmap`.
2. **Dockerize Postgres:** In `docker-compose.yml`, add services for PostgreSQL (with pgvector) and Redis as shown above. Use environment variables for credentials. Ensure `postgres` service has `POSTGRES_DB=Kontexa_db`, etc.
3. **Database config:** In FastAPI settings, add `DATABASE_URL` and `REDIS_URL` (read from `.env`). Use SQLAlchemy Async and include `asyncpg` in dependencies.
4. **Install dependencies:** Add `psycopg`, `asyncpg`, `sqlalchemy[asyncio]`, `alembic`, `pgvector`, and any ORM (Pydantic if used).
5. **SQLAlchemy models:** Create `backend/app/models` directory. Add `Base = declarative_base()` and model classes per schema above. Include `__tablename__`, columns, and relationships. Use `server_default=func.now()` for timestamps.
6. **Alembic setup:** Run `alembic init alembic`. Configure `alembic.ini` (set sqlalchemy.url to `env database URL`). In `alembic/env.py`, import your models so it can `run_sync(Base.metadata.create_all)` if generating.
7. **Initial migration:** Create `alembic/versions/001_initial.py` with `op.create_table` for `users`, `workspaces`, `workspace_members`, `projects`. Include `op.create_index` for foreign keys/unique constraints. Use `UUID(as_uuid=True)`.
8. **Apply migrations locally:** Run `alembic upgrade head` on the development DB.
9. **Iterate building schema:** Repeat for subsequent migrations (authentication, chat, documents, memory, etc.), following the plan above. Generate a new revision for each phase.
10. **Test DB layer:** Write a simple script or test to create a new user/workspace and ensure relations and default values work. 
11. **Add fixtures:** In `tests/conftest.py`, add Pytest fixtures to create/drop tables using SQLAlchemy or Alembic.
12. **Validate indexes:** After migrations, verify indexes exist (psql `\d+ table`).
13. **Documentation:** Add all relevant docs files under `docs/` and `docs/roadmap/` (see below for file list).
14. **CI config:** Update GitHub Actions to run migrations and tests as above.
15. **Quality check:** Ensure migrations apply cleanly and tests pass without errors.

### Acceptance Criteria

- All tables (per schema) are created with correct columns, types, keys, and indexes.  
- `pgvector` extension is installed and vector columns are created.  
- Alembic migrations can be applied in order on a blank database.  
- SQLAlchemy models match the database schema.  
- Basic CRUD operations (via the ORM) work in tests.  
- No missing dependencies; linter/formatter checks pass.

---

## Files to Create

The following **Markdown files** should be added to the `docs/` directory (and `docs/roadmap/`) of the repo:

- **`docs/ROADMAP.md`** – High-level project roadmap, listing phases 0–N (each with summary of goals).  
- **`docs/ARCHITECTURE.md`** – System architecture overview (diagram + description of components: Next.js, FastAPI, Postgres, Redis, AI providers, etc.). Include the deployment mermaid topology diagram.  
- **`docs/DATABASE.md`** – Detailed database design document (everything in *Database Design* section above). ER diagram (mermaid), full schema, indexing, tenant strategy, and reference patterns.  
- **`docs/DEPLOYMENT.md`** – Deployment plan and hosting comparison. Include the provider comparison table and recommended setups (based on above).  
- **`docs/DEVELOPMENT.md`** – Local development guide: Docker Compose, environment vars, how to run API, integrate Postgres/Redis locally.  
- **`docs/TESTING.md`** – Testing strategy: Pytest setup, fixtures, CI pipeline snippet, etc.  
- **`docs/AGENT_INSTRUCTIONS.md`** – Summarize the above agent tasks in checklist form for automated implementation.  
- **`docs/ROADMAP.md`** – (Same as above; if you consider one file the master roadmap).  

Under **`docs/roadmap/`** (phase-wise implementation):

- `00-foundation.md` – Project setup: repo scaffolding, linting, formatting, initial CI, Docker Compose with backend+frontend+db+redis.  
- `01-database.md` – *This phase.* Steps to connect FastAPI to Postgres (with pgvector), create models, migrations, etc. (As per Agent Tasks above).  
- `02-authentication.md` – Next: User auth (fastapi-users or custom JWT), OAuth, user sessions.  
- `03-workspace.md` – Workspace & project scaffolding (invites, membership).  
- `04-chat.md` – Conversations and messaging implementation.  
- `05-rag.md` – Document ingestion, chunking, embedding integration.  
- `06-memory.md` – Memory pipeline (store/retrieve semantic memory).  
- `07-integrations.md` – GitHub/Slack/Notion integration connectors.  
- `08-tool_caller.md` – Register tools and invoke them.  
- `09-agentic.md` – Agent orchestration (LangGraph-like plans).  
- `10-ops-security.md` – Observability, logging, policies (later phases).

*(Even if some phases aren’t implemented yet, listing them guides future work.)*

Each `docs/roadmap/NN-*.md` should follow a consistent format: 

- **Objective:** What to build.  
- **Scope & Architecture:** High-level design.  
- **Database changes:** New tables/fields.  
- **Backend:** API changes, new models or endpoints.  
- **Frontend:** UI changes or new API calls.  
- **Tests:** Key tests to write.  
- **Definition of Done:** Criteria for completion.  

This structure helps an AI agent or developer to implement each phase systematically. 

---

## Sources

- PostgreSQL official documentation (UUID, JSONB, VACUUM, pg_dump, etc.).  
- pgvector docs (creating vector columns, indexes).  
- SQLAlchemy Async docs for session usage.  
- Alembic tutorial.  
- AWS blog on RLS multi-tenancy.  
- Industry blog on Postgres hosting (Railway).  

