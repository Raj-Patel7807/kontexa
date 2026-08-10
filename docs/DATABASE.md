# Executive Summary

For **Kontexa** we recommend a modern PostgreSQL-based architecture with tight multi-tenancy and vector search support.  We use one **shared database** (pool model) with every table tagged by `workspace_id`, and enforce isolation via policy (e.g. Row-Level Security).  All data (users, workspaces, projects, conversations, messages, documents, etc.) lives in PostgreSQL, with vector embeddings stored in a `VECTOR` column (via the [pgvector](https://github.com/pgvector/pgvector) extension).  This keeps relational and semantic data together, enabling “hybrid” queries (structured + similarity) in one system.  

We adopt **UUID primary keys**, `timestamptz` timestamps, soft-delete (`deleted_at`) flags with partial indexes, and JSONB for flexible fields.  Heavy tables (e.g. chat messages, embeddings) can be range-partitioned by time or tenant to speed queries and allow easy archival.  For example, old partitions can be dropped in bulk instead of slow `DELETE`s.  We add appropriate indexes: B-tree for FKs and queries, GIN for JSONB content, and `USING ivfflat(...)` or `USING hnsw(...)` for the vector columns.  

In the short term (MVP), we’ll use a **managed Postgres** provider to minimize ops overhead.  Viable free-tier/low-cost options in 2026 include **Neon** (serverless Postgres, 100 CU-hours + 0.5 GiB free, includes time-travel/PITR), **Supabase** (500 MB free, free PITR backup), **Aiven** (free 1 GB, auto-backups), or **Timescale/TigerData** (750 MB free, includes pgvector).  We’ll run the FastAPI backend on a simple Docker container (or Railway), and front-end on Vercel with HTTPS.

Operationally, we enable automated backups/PITR (most providers include it), monitor with `pg_stat_statements` and PgBouncer as needed, and schedule regular VACUUM/REINDEX.  Soft-deleted or aged data beyond retention windows can be purged via scheduled jobs or by dropping old partitions.  We enforce security best practices: encrypted connections, least-privileged DB roles, secrets in vault/ENV, and RLS policies to filter out other tenants’ data.  

The attached sections include: 

- **`DATABASE.md`** – database philosophy, entity list, ER diagram (Mermaid), and rationale.  
- **`docs/roadmap/01-database.md`** – step-by-step implementation plan for an AI agent.  
- **`DDL.sql`** – SQL DDL to create tables, indexes, extensions, with partitioning example.  
- **SQLAlchemy Models & Alembic** – sample ORM class snippets and migration outline.  
- **Deployment** – local (Docker Compose) and cloud options, architecture diagram (Mermaid), connection string examples.  
- **Scaling & Operations** – backup/PITR, VACUUM/reindex, partition archiving, etc.  
- **Security Checklist** – roles, RLS, encryption, etc.  
- **Testing & Acceptance Criteria** – key tests and validation.  
- **Agent Tasks** – explicit to-do commands for an AI coder.

All recommendations are drawn from current Postgres best practices and recent sources.

# DATABASE.md

## Philosophy

- **Shared Database, Pool Model** – We use a single PostgreSQL database for all tenants (workspaces). Every table includes a `workspace_id` (UUID FK) to mark its tenant. This “pool” approach minimizes resource overhead.  We enforce data isolation centrally via database policies (see RLS below) rather than relying on app logic alone.  

- **Multi-Tenancy Isolation** – All queries filter by workspace. E.g. every table (users, projects, messages, etc.) has `workspace_id NOT NULL`. Optionally, enable [Row-Level Security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html) with a policy like `USING (workspace_id = current_setting('app.current_workspace')::uuid)` to automatically hide other tenants’ rows. This assures no cross-tenant leaks.  

- **UUID Primary Keys** – Use `UUID` (v4) as default PKs with `gen_random_uuid()` (or `uuid_generate_v4()`) default. This avoids guessable IDs and scales better in distributed systems. (E.g. `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`.)  

- **Timestamps & Soft Deletes** – All tables have `created_at TIMESTAMPTZ DEFAULT NOW()`, `updated_at TIMESTAMPTZ DEFAULT NOW()`, and a nullable `deleted_at TIMESTAMPTZ`.  Rows are “soft-deleted” by setting `deleted_at`; queries include `WHERE deleted_at IS NULL`.  We index on this column (e.g. `CREATE INDEX idx_X_deleted ON X(deleted_at) WHERE deleted_at IS NULL`) to speed active-row queries.  Optionally, RLS policies can also hide soft-deleted rows.  

- **JSONB for Flexibility** – Some columns store semi-structured data (e.g. `metadata JSONB`, integration configs, webhooks, etc.).  Use PostgreSQL’s `JSONB` type for these.  Add **GIN indexes** on JSONB when needed to accelerate key/value queries. For example, if searching by `metadata->>'key'`, use `CREATE INDEX ON table USING GIN (metadata)` or an expression index on `metadata->'key'`.  

- **Vector Search with pgvector** – We include the `vector` extension to store embedding vectors (e.g. for document chunks).   This means we can perform ANN (Approximate Nearest Neighbor) queries right in SQL.  For each table with embeddings, we create an index: typically `USING ivfflat` for an initial rollout.  Example:  
  ```sql
  CREATE INDEX ON document_chunks
    USING ivfflat (embedding vector_l2_ops)
    WITH (lists = 100);
  ```  
  (This uses L2 distance; for cosine or inner-product, use `vector_cosine_ops` or `vector_ip_ops`.)  Later, we may benchmark HNSW indexes for performance.  In queries, always filter by workspace (or other structured conditions) *before* the vector search (“hybrid retrieval”) to reduce the candidate set.  

- **Partitioning & Archival** – Very large tables (like chat messages or logs) should be *partitioned*.  For instance, partition `messages` or `audit_logs` by **date range** or by workspace (list partition) if applicable.  This way older partitions can be dropped or moved cheaply.  Dropping a partition (or detaching it) is far faster than a DELETE and avoids heavy vacuum costs.  As an example:  
  ```sql
  CREATE TABLE messages (
    ... common columns ...
    created_at TIMESTAMPTZ NOT NULL,
    ...
  ) PARTITION BY RANGE (created_at);

  CREATE TABLE messages_2026_08 PARTITION OF messages
    FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');
  ```  
  We pick a partition key aligned with query patterns (often date or workspace).  Stale data (e.g. older than N months) can then be purged by dropping partitions or running archival jobs.

## Data Model & ER Diagram

Below is the high-level schema. Every table’s `workspace_id` FK ties data to a tenant. The ER diagram (Mermaid) highlights relationships:

```mermaid
erDiagram
    USERS {
      UUID id PK
      text email
      text name
      bool is_active
      timestamptz created_at
    }
    WORKSPACES {
      UUID id PK
      text name
      text slug
      timestamptz created_at
    }
    WORKSPACE_MEMBERS {
      UUID workspace_id FK
      UUID user_id FK
      text role
    }
    PROJECTS {
      UUID id PK
      UUID workspace_id FK
      text name
      text slug
      text status
      timestamptz created_at
    }
    CONVERSATIONS {
      UUID id PK
      UUID workspace_id FK
      UUID project_id FK
      text title
      bool is_active
      timestamptz created_at
    }
    MESSAGES {
      UUID id PK
      UUID conversation_id FK
      UUID user_id FK
      text content
      jsonb metadata
      timestamptz created_at
    }
    MESSAGE_PARTS {
      UUID id PK
      UUID message_id FK
      int part_index
      text content
      varchar mime_type
    }
    INTEGRATIONS {
      UUID id PK
      UUID workspace_id FK
      varchar type
      jsonb config
      bool enabled
      timestamptz created_at
    }
    DOCUMENTS {
      UUID id PK
      UUID project_id FK
      text title
      jsonb metadata
      timestamptz created_at
    }
    DOCUMENT_VERSIONS {
      UUID id PK
      UUID document_id FK
      text content
      timestamptz created_at
    }
    DOCUMENT_CHUNKS {
      UUID id PK
      UUID document_version_id FK
      int chunk_index
      text content
      vector embedding
      timestamptz created_at
    }
    MEMORY_ENTRIES {
      UUID id PK
      UUID workspace_id FK
      UUID user_id FK
      text key
      text content
      timestamptz created_at
    }
    TOOLS {
      UUID id PK
      UUID project_id FK
      text name
      jsonb config
      timestamptz created_at
    }
    AGENT_RUNS {
      UUID id PK
      UUID tool_id FK
      jsonb inputs
      jsonb outputs
      varchar status
      timestamptz started_at
      timestamptz ended_at
    }
    AI_PROVIDERS {
      UUID id PK
      text name
      jsonb config
      timestamptz created_at
    }
    AI_MODELS {
      UUID id PK
      UUID provider_id FK
      text model_name
      timestamptz created_at
    }
    AI_USAGE {
      UUID id PK
      UUID user_id FK
      UUID model_id FK
      UUID workspace_id FK
      int tokens_used
      int cost_cents
      timestamptz timestamp
    }
    AUDIT_LOGS {
      BIGSERIAL id PK
      UUID workspace_id
      text action
      text table_name
      UUID record_id
      jsonb changes
      timestamptz created_at
    }

    USERS ||--o{ WORKSPACE_MEMBERS : "member of"
    WORKSPACES ||--o{ WORKSPACE_MEMBERS : "has user"
    WORKSPACES ||--o{ PROJECTS : "owns"
    WORKSPACES ||--o{ CONVERSATIONS : "contains"
    WORKSPACES ||--o{ INTEGRATIONS : "configures"
    WORKSPACES ||--o{ MEMORY_ENTRIES : "stores"
    WORKSPACES ||--o{ AUDIT_LOGS : "records"
    PROJECTS ||--o{ CONVERSATIONS : "includes"
    PROJECTS ||--o{ DOCUMENTS : "contains"
    PROJECTS ||--o{ TOOLS : "defines"
    CONVERSATIONS ||--o{ MESSAGES : "holds"
    MESSAGES ||--o{ MESSAGE_PARTS : "split into"
    DOCUMENTS ||--o{ DOCUMENT_VERSIONS : "versions"
    DOCUMENT_VERSIONS ||--o{ DOCUMENT_CHUNKS : "chunks"
    TOOLS ||--o{ AGENT_RUNS : "executes"
    AI_PROVIDERS ||--o{ AI_MODELS : "provides"
    AI_MODELS ||--o{ AI_USAGE : "logged by"
```

### Key Tables

- **`users`**: Global user accounts.  Columns: `id` (UUID PK), `email` (unique), `name`, `is_active` (soft-delete flag), plus timestamps.  We index on `(deleted_at IS NULL)` to find active users quickly.
- **`workspaces`**: Tenant organizations. Columns: `id`, `name`, `slug` (unique per tenant), etc.  A `workspace` may have many users and projects.
- **`workspace_members`**: Link table (many-to-many) between users and workspaces, with a role (admin/member).  
- **`projects`**: Projects under a workspace. Contains `workspace_id`, `name`, `slug` (unique within workspace), `status` (e.g. active/archived), etc. Unique index on `(workspace_id, slug)`.
- **Chat (`conversations`,`messages`,`message_parts`)**:  
  - `conversations`: Per-workspace and optional project. Columns: `id`, `workspace_id`, `project_id`, `title`, `is_active`, timestamps.  
  - `messages`: Linked to a conversation. Columns: `id`, `conversation_id`, `user_id` (sender), `content`, `metadata` (JSONB), timestamps.  Index on `conversation_id`.  
  - `message_parts`: In case large messages are chunked. Each part has `id`, `message_id`, `part_index`, `content`, `mime_type`, timestamp.  

- **`integrations`**: Stores external connector configs (GitHub, Slack, Jira, etc.). Fields: `workspace_id`, `type` (e.g. ‘github’), `config` (JSONB for tokens/settings), `enabled` flag, timestamps. The actual data fetched from these services is not mirrored entirely; instead, relevant documents (below) are stored.  

- **RAG (Documents)**:  
  - `documents`: High-level records (e.g. a Notion page, GitHub PR, Slack thread) in a project. Contains `project_id`, `title`, `metadata` (JSONB), etc.  
  - `document_versions`: If documents can update (e.g. new versions of a file), this table holds each version’s content.  
  - `document_chunks`: Each version is split into chunks. Columns: `document_version_id`, `chunk_index`, `content` (text) and `embedding VECTOR`. We add a vector index here.  

- **`memory_entries`**: (Optional) For long-term agent memory. Columns: `workspace_id`, `user_id`, `key` (topic), `content`, `created_at`. Indexed on `workspace_id`.  

- **Tools & Agents**:  
  - `tools`: Custom actions or tools defined per project (e.g. web search, code executor). Fields: `project_id`, `name`, `config` (JSONB for tool parameters).  
  - `agent_runs`: Each invocation of a tool or an AI agent. Fields: `tool_id`, `inputs` (JSONB), `outputs` (JSONB), `status`, start/end timestamps.  

- **AI Metadata**:  
  - `ai_providers`: Registered AI providers (e.g. OpenAI, Anthropic). Columns: `name`, `config` (API keys or settings).  
  - `ai_models`: Supported models under each provider. Columns: `provider_id`, `model_name` (e.g. `gpt-4`), `max_tokens`, etc.  
  - `ai_usage`: Logs of API usage. Columns: `user_id`, `workspace_id`, `model_id`, `tokens_used`, `cost_cents`, `timestamp`. Index on `model_id` for aggregation.  

- **`audit_logs`**: Security/compliance audit trail. This is a generic log table (see audit section) with fields like `action`, `table_name`, `record_id`, `changes` (JSONB), `user`, `timestamp`. We index common queries, e.g. by workspace and time.  

We should **not** try to mirror entire external systems.  For example, we do NOT import Slack’s full message DB or GitHub’s repos schema.  We only store *selected* data relevant to Kontexa’s use cases (e.g. PR descriptions, chat snippets), usually in the Documents/Chunks tables.

All relationship constraints use `ON DELETE CASCADE` or `SET NULL` appropriately so that deleting a workspace or project cleans up child data.  The schema balances normalization (for consistency) with flexibility (using JSONB for dynamic fields).

## Tenant Isolation

We enforce tenant data isolation by:
- Always including `workspace_id` (FK) on private tables.
- Adding **RLS policies** (PostgreSQL 9.5+) if we want the DB itself to block cross-tenant access.  For example:  
  ```sql
  ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
  CREATE POLICY conv_isolation ON conversations
    USING (workspace_id::TEXT = current_setting('app.current_workspace')::TEXT);
  ```  
  This makes Postgres automatically apply `WHERE workspace_id = current_app` to every SELECT/INSERT, etc..  The application sets `app.current_workspace` session variable per request.

# docs/roadmap/01-database.md

```markdown
# Phase 1 — Database Foundation

**Objective:** Design and implement the core database layer (PostgreSQL) with all foundational tables and migration support.

## Goals

- Define and document the database schema for Kontexa (tables listed above).
- Set up **SQLAlchemy** (asyncpg dialect) and **Alembic** for migrations.
- Ensure local dev environment runs PostgreSQL + pgvector + Redis via Docker.
- Create initial migrations and sample data.

## Steps (Agent Tasks)

1. **Create Branch:** `git switch -c feat/database-foundation`.
2. **Setup Docker Compose:** In `docker-compose.yml`, add services:
   - `postgres:15` with volumes for data and ports mapped, enabling `vector` extension.
   - `redis:latest` (for caching).
   - (Optionally `pgadmin` for inspection).
3. **Configure Extensions:** In an init script or migrations, run:
   ```sql
   CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
4. **Initialize Alembic:**  
   - Run `alembic init migrations`.  
   - In `alembic/env.py`, set `sqlalchemy.url` from `DATABASE_URL` env var.
5. **Create Initial Migration:**  
   ```bash
   alembic revision -m "Initial schema"
   ```  
   Edit the new file (e.g. `versions/xxxxx_initial_schema.py`) to `op.create_table` for all core tables:
   - `users, workspaces, workspace_members, projects, conversations, messages, message_parts, integrations, documents, document_versions, document_chunks, memory_entries, tools, agent_runs, ai_providers, ai_models, ai_usage, audit_logs`.
   - Use UUID columns (`sa.UUID`), JSONB, TIMESTAMPTZ.
   - Add primary keys, foreign keys, and `ON DELETE CASCADE/SET NULL` rules.
   - Add unique constraints (e.g. `(workspace_id, slug)` on projects).
   - Add partial indexes on `deleted_at` columns (`postgresql_where="deleted_at IS NULL"`).
   - Add GIN indexes for JSONB if needed.
   - Add vector index:
     ```python
     op.execute("CREATE INDEX idx_chunks_embedding ON document_chunks USING ivfflat (embedding vector_l2_ops) WITH (lists = 100)")
     ```
6. **Run Migrations Locally:**  
   - Start containers: `docker-compose up -d`.  
   - Ensure DB is accessible (e.g. `psql` to check).  
   - Run `alembic upgrade head`.  
   - Verify tables: use `\d` or `psql -c '\dt'`.
7. **Implement SQLAlchemy Models:**  
   - In `backend/models/*.py`, define `User`, `Workspace`, `Project`, etc. with `id = Column(UUID, default=uuid4, primary_key=True)`, etc.
   - Establish relationships (e.g. `workspace = relationship("Workspace")`).
   - Use `ServerDefault(sa.text("now()"))` for timestamps or SQLAlchemy `func.now()`.
8. **Test Database Operations:**  
   - Write unit tests (pytest) to insert/read each table via SQLAlchemy.
   - For each model, test: create a record, query by its fields (including JSONB filters), and soft-delete then ensure it’s hidden by default.
   - Test vector insertion/query: insert a `document_chunk` with an embedding (e.g. `embedding = [1,2,3]`), then query nearest neighbors (`ORDER BY embedding <-> '[1,2,3]'`).
9. **Document Schema:**  
   - Fill out `docs/ARCHITECTURE.md` or a dedicated `DATABASE.md` with the schema overview (the content above).  
   - Include the Mermaid ER diagram code.
   - Write or update `docs/DATABASE.md` with the design rationales and table descriptions above.
10. **Commit & Push:**  
   ```bash
   git add .
   git commit -m "feat: initial database schema and migrations"
   git push -u origin feat/database-foundation
   ```
   
## Acceptance Criteria

- All listed tables exist in the development database with correct columns and constraints.
- SQLAlchemy models align with the table definitions (tests should pass).
- Alembic history has a working migration that creates the schema.
- Basic data (one workspace, user, project, conversation) can be created via the API or scripts.
- Partial indexes and vector index are present (`\di+` in psql).
- Documentation (`DATABASE.md` and ER diagram) is completed and matches the implemented schema.

```

# DDL.sql

```sql
-- Enable extensions for UUIDs and vector support
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Users (global accounts)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
-- Index active users (soft-delete)
CREATE INDEX idx_users_deleted ON users(deleted_at) WHERE deleted_at IS NULL;

-- Workspaces (tenants)
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_workspaces_deleted ON workspaces(deleted_at) WHERE deleted_at IS NULL;

-- User memberships in workspaces
CREATE TABLE workspace_members (
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    PRIMARY KEY (workspace_id, user_id)
);
CREATE INDEX idx_workspace_members_user ON workspace_members(user_id);

-- Projects within a workspace
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
-- Unique per workspace
CREATE UNIQUE INDEX idx_projects_workspace_slug ON projects(workspace_id, slug);
CREATE INDEX idx_projects_deleted ON projects(deleted_at) WHERE deleted_at IS NULL;

-- Chat conversations
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    title TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_conversations_workspace ON conversations(workspace_id);
CREATE INDEX idx_conversations_deleted ON conversations(deleted_at) WHERE deleted_at IS NULL;

-- Messages in a conversation
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_messages_conversation ON messages(conversation_id);

-- Parts of a large message (optional)
CREATE TABLE message_parts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    part_index INT NOT NULL,
    content TEXT,
    mime_type VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_message_parts_msg ON message_parts(message_id);

-- External integrations (GitHub, Slack, etc.)
CREATE TABLE integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    config JSONB,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_integrations_workspace ON integrations(workspace_id);

-- Documents for RAG / indexed knowledge
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Versions of documents (for tracking edits)
CREATE TABLE document_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Chunks of document text with embeddings
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_version_id UUID NOT NULL REFERENCES document_versions(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1536),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- Vector index on embeddings (approximate nearest neighbor)
CREATE INDEX idx_chunks_embedding ON document_chunks
    USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);

-- Long-term memory entries
CREATE TABLE memory_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID,
    key TEXT,
    content TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_memory_workspace ON memory_entries(workspace_id);

-- Tools (custom actions) per project
CREATE TABLE tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    config JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Agent or tool execution runs
CREATE TABLE agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id UUID NOT NULL REFERENCES tools(id) ON DELETE SET NULL,
    inputs JSONB,
    outputs JSONB,
    status VARCHAR(20),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ
);
CREATE INDEX idx_agent_runs_tool ON agent_runs(tool_id);

-- AI providers (e.g. OpenAI, AzureAI)
CREATE TABLE ai_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    config JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- AI models (e.g. gpt-4, PaLM2) per provider
CREATE TABLE ai_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id UUID NOT NULL REFERENCES ai_providers(id) ON DELETE CASCADE,
    model_name TEXT NOT NULL,
    max_tokens INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_ai_models_provider ON ai_models(provider_id);

-- AI usage logs (tokens, cost)
CREATE TABLE ai_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    model_id UUID NOT NULL REFERENCES ai_models(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    tokens_used BIGINT NOT NULL DEFAULT 0,
    cost_cents BIGINT NOT NULL DEFAULT 0,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_ai_usage_model ON ai_usage(model_id);

-- Audit logs (trigger-based or pgAudit can populate this)
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    workspace_id UUID NOT NULL,
    user_id UUID,
    action VARCHAR(50) NOT NULL,
    table_name VARCHAR(50),
    record_id UUID,
    changes JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_audit_workspace ON audit_logs(workspace_id);
CREATE INDEX idx_audit_time ON audit_logs(created_at);

-- Example: Partition old messages by month (for archival)
CREATE TABLE messages_2026_08 PARTITION OF messages
    FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');
```

# SQLAlchemy Models & Alembic Migrations

Below are representative examples (not full code) to guide the implementation.

```python
# Example SQLAlchemy declarative models (async)
from sqlalchemy import Column, String, Text, Boolean, TIMESTAMP, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(TIMESTAMP)

class Workspace(Base):
    __tablename__ = "workspaces"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    slug = Column(String, nullable=False, unique=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(TIMESTAMP)

class Project(Base):
    __tablename__ = "projects"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False)
    status = Column(String, nullable=False, default="active")
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(TIMESTAMP)
```

**Alembic Example (python migration file):**

```python
def upgrade():
    op.create_table(
        'workspaces',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.TIMESTAMP()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('slug')
    )
    # ... create other tables similarly ...
    # Partial index for soft delete:
    op.create_index('idx_workspaces_deleted', 'workspaces', ['deleted_at'], unique=False,
                    postgresql_where=sa.text('deleted_at IS NULL'))
    # Vector index for embeddings:
    op.execute("CREATE INDEX idx_chunks_embedding ON document_chunks "
               "USING ivfflat (embedding vector_l2_ops) WITH (lists = 100)")
```

After writing models and migrations:

```bash
# Generate migration based on models (optional):
alembic revision --autogenerate -m "Create users, workspaces, projects..."
alembic upgrade head
```

No items in this phase should rely on external services; focus is on the local schema. 

# Deployment Guidance

## Local Development

Use **Docker Compose** to run the stack locally:

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=Kontexa
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:latest
    ports:
      - "6379:6379"

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    environment:
      DATABASE_URL: "postgresql+asyncpg://postgres:postgres@postgres:5432/Kontexa"
      REDIS_URL: "redis://redis:6379"

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  pgdata:
```

- The `backend` service runs FastAPI. It connects via `DATABASE_URL` and `REDIS_URL`.
- The `postgres` service should have the `vector` extension enabled (Postgres 15+). We can run `CREATE EXTENSION vector;` in the init or migration.
- With this, you can `docker-compose up`, then run migrations (`alembic upgrade head`) inside `backend` container.
- Use a `.env` file or Docker secrets to provide credentials in real setups.

## Cloud Providers (2026 Options)

For the production MVP (cost-conscious):

- **Frontend**: Deploy on Vercel (free tier for hobby sites) with your Next.js app.
- **Backend + DB**: Options include:
  - **Neon** (serverless Postgres): Free 100 CU-hours + 0.5 GiB. Supports pgvector, has built-in PITR. Use Neon’s branchable DB or main DB with `DATABASE_URL` from Neon.
  - **Supabase**: Free tier (1 vCPU, 0.5 GiB), includes Postgres + Auth. `supabase.com` provides a connection string. It supports pgvector and daily backups/PITR.
  - **Aiven PostgreSQL**: Free (2 vCPU, 1 GiB). Managed backups included.  
  - **Timescale Cloud (TigerData)**: Free 750 MB (including pgvector) with PITR.
  - **Railway / Render**: No persistent free tier (just credits), so less ideal long-term.
  - **AWS RDS/Aurora**: $12+/month after credits. Offers multi-AZ, full backup/PITR, but higher cost.
- **Redis**: Use managed (e.g. Redis Cloud free plan) or use Railway’s Redis. Keep it ephemeral.

### Production Architecture

```mermaid
flowchart LR
    Client[User Device] -- HTTPS --> Vercel[Vercel: Next.js Frontend]
    Vercel --> FastAPI[Backend (FastAPI)]
    FastAPI --> Postgres[(PostgreSQL + pgvector)]
    FastAPI --> Redis[(Redis Cache)]
    FastAPI --> OpenAI[OpenAI API]
    FastAPI --> GitHub[GitHub API]
    FastAPI --> Slack[Slack API]
    FastAPI --> Jira[Jira API]
    Note1[Managed Providers: Neon/Supabase/Aiven/etc] --- Postgres
    Note2[Managed Redis or self-hosted] --- Redis
```

- **Connections:** The backend uses a connection string like `postgresql+asyncpg://user:pass@host:port/dbname?sslmode=require` (use SSL). Secrets (DB credentials, API keys) should be in environment variables or a secrets manager. 
- **DNS and Security:** Use Vercel’s built-in HTTPS. For the backend DB, restrict access to only from your app (via security groups/VPC). 

## Provider Comparison (2026)

| Provider         | Free Tier                | Notes                                          |
|------------------|--------------------------|------------------------------------------------|
| **Neon**         | 100 CU-hrs, 0.5 GiB | Serverless, auto-scaled. Includes time-travel/PITR.  |
| **Supabase**     | 0.5 GiB (1 vCPU)      | Postgres+Auth. Free PITR backups.   |
| **Aiven**        | 1 GiB (2 vCPU)     | Regional DB. Automatic backups included. |
| **TigerData**    | 750 MB (free)       | Based on Timescale. Supports pgvector. Free PITR. |
| **Railway**      | $1 credit/month (no real free)  | Short credits, not ideal long-term.          |
| **AWS RDS**      | $200 credit (new acct) | Minimum ~$12/mo after credits. Good uptime. |

*(Costs/pricing from Bytebase (2026))*

For MVP, Neon or Supabase are easiest: they give a Postgres URL and handle autoscaling. They both support pgvector out of the box. We can migrate our local schema by running Alembic with the production `DATABASE_URL`.

### Secrets and Config

- **Environment Variables**: Store `DATABASE_URL`, `REDIS_URL`, `OPENAI_API_KEY`, etc. in env vars or Vercel secrets. Do NOT hard-code credentials.
- **Encryption**: Enable SSL for Postgres. Managed services typically encrypt data at rest by default.
- **Network**: Use private networking/VPC wherever possible. E.g. Railway provides private networking between services.

# Scaling & Operations

- **Backups/PITR:** Ensure automatic backups are enabled. For example, AWS RDS offers free backups up to DB size; Neon and others include continuous backups/PITR. Keep at least 7–30 days of point-in-time recovery for production data.
- **Vacuum & Reindex:** With active writes, use PostgreSQL’s autovacuum. For very large tables (e.g. messages, audit_logs) consider scheduling periodic `VACUUM (FULL)` during low traffic. After bulk deletes or major loads, run `VACUUM` and `ANALYZE`.
- **Monitoring:** Enable `pg_stat_statements` to track slow queries. Use tools (Prometheus exporters or hosted dashboards) to monitor connections, cache hit ratios, index usage. Investigate high-load queries (e.g. vector searches) for optimization.
- **Partition Maintenance:** For any partitioned table (e.g. monthly messages), set up a **cron job or pg_cron** to:
  - **Create upcoming partition** before use.
  - **Drop old partitions** beyond retention period. Dropping is instantaneous vs scanning to delete.
- **Scaling Out:** Initially, one Postgres instance is fine. If load grows, consider:
  - **Read replicas** for analytics or reporting queries (cache AI usage logs, audit data).
  - **Horizontal sharding** (not yet needed; providers like PlanetScale Postgres are emerging). Note: PlanetScale Postgres will soon offer horizontal sharding (via “Neki” project).
- **Disaster Recovery:** Test restore processes (e.g. on Neon or AWS). Keep backups in a separate region if possible.

# Security Checklist

- **Access Control:** Use non-superuser roles for your application. E.g. create an `app_user` role with only `CONNECT` on DB and `SELECT/INSERT/UPDATE/DELETE` on *needed* tables. Create a separate `read_only` role with only `SELECT`.  
- **Row-Level Security:** As mentioned, enable RLS on sensitive tables (e.g. conversations, messages) so that each workspace can only see its own data. Also use RLS for soft deletes: e.g.  
  ```sql
  ALTER TABLE users ENABLE ROW LEVEL SECURITY;
  CREATE POLICY hide_deleted ON users FOR SELECT USING (deleted_at IS NULL);
  ```  
  This hides soft-deleted rows automatically.
- **Encryption:** Use SSL/TLS for DB connections. Managed services encrypt at rest by default. If storing very sensitive fields (passwords, tokens), consider `pgcrypto` or client-side encryption.
- **Secrets Management:** Do NOT commit any secrets. Use environment vars, .gitignore `.env`, or a secrets manager (AWS Secrets Manager, HashiCorp Vault).
- **SQL Injection:** Use parameterized queries (SQLAlchemy ORM or query parameters). Never concatenate raw inputs into SQL.
- **Database Users/Privileges:** Revoke `CREATE` on public schema if not needed. Use `GRANT` to limit schema usage. E.g.:  
  ```sql
  REVOKE CREATE ON SCHEMA public FROM PUBLIC;
  CREATE ROLE reader NOINHERIT;
  GRANT CONNECT ON DATABASE Kontexa TO reader;
  GRANT USAGE ON SCHEMA public TO reader;
  GRANT SELECT ON ALL TABLES IN SCHEMA public TO reader;
  ```
- **Audit Logs:** We keep an `audit_logs` table (or use pgAudit) to record important actions (logins, config changes). Ensure only admins can query full logs.  
- **Network Security:** Restrict DB inbound rules (whitelist app server IPs). Close unused ports.  
- **Dependency Security:** Keep Postgres, extensions, and libraries (SQLAlchemy, asyncpg) up-to-date with security patches.

# Testing and Acceptance Criteria

- **Schema Tests:** Verify each table and index exists. For example, with `psql` or SQLAlchemy introspection: ensure FK constraints and partial indexes are in place.
- **CRUD Tests:** For each model, write automated tests that create/read/update/delete records. E.g. create a user, fetch by email; create a project in a workspace, ensure it can’t be seen from another workspace ID.
- **Multi-Tenancy Tests:** Attempt cross-tenant access: e.g. set one `current_workspace` and try to access another’s data; RLS should prevent it.
- **Soft Delete Tests:** After “deleting” (setting `deleted_at`), verify it does not appear in “active” queries (via RLS or WHERE clause), but can be recovered by clearing `deleted_at`.
- **Vector Query Test:** Insert sample document chunks with known embeddings. Run a vector similarity query (`ORDER BY embedding <-> [vector] LIMIT 5`) and check the results are correct and use the index (EXPLAIN should show `Index Scan` on the ivfflat index).
- **Partitioning Test:** If partitions are created, test that inserts outside any partition range fail, and that dropping a partition removes data quickly.
- **Migration Test:** On a fresh DB, run `alembic upgrade head` and ensure no errors. On an existing DB, run migrations to simulate upgrades.
- **Backup/Restore Test:** If possible, simulate a point-in-time recovery or restore from a dump to verify backup integrity.
- **Performance Smoke:** With a modest data volume (e.g. 10k messages, 1k chunks), measure query response times for key operations (simple select, vector search). Ensure acceptable (e.g. <200ms).
- **Security Tests:** Attempt injection attacks (SQL injection) and verify they fail or are parameterized. Ensure unauthorized roles cannot read data.
- **Agentic Tasks Validation:** Ensure all agent instructions (below) have been executed successfully in order.

# Agent Instructions (Concrete Tasks)

1. **Switch Branch:** `git switch -c feat/database-foundation`.
2. **Pull Dependencies:** In backend, install SQLAlchemy, Alembic:  
   ```bash
   pip install sqlalchemy[asyncio] asyncpg alembic psycopg2-binary
   ```
3. **Database Container:** Start Docker services: `docker-compose up -d postgres redis`. Ensure `vector` extension is available (`psql -c "CREATE EXTENSION vector;"`).
4. **Initialize Alembic:** `alembic init migrations`. Edit `alembic.ini` or `env.py` to use `env.get("DATABASE_URL")`.
5. **Create Migration:** `alembic revision -m "Initial schema"`. Open the file in `migrations/versions/`.
6. **Edit Migration:** Add `op.create_table` for each table as per DDL above, using `sa.Column`. Also add `op.create_index` lines.
7. **Apply Migration:** `alembic upgrade head`. Check tables: `psql -c "\d+"`.
8. **Write Models:** Create SQLAlchemy models (as above) in `models/`. Ensure `metadata = Base.metadata`.
9. **Run Tests:** Write a quick script or pytest file to: connect to DB, insert a test workspace, user, project. Fetch them back. Confirm nothing fails.
10. **Vector Insert Test:** Use `asyncpg` or SQLAlchemy:  
    ```python
    conn.execute("INSERT INTO document_chunks (id, document_version_id, chunk_index, content, embedding) VALUES (gen_random_uuid(), 'existing-uuid', 1, 'hello', '[1,2,3]')")
    result = conn.fetch("SELECT id FROM document_chunks ORDER BY embedding <-> '[1,2,3]' LIMIT 1")
    ```
11. **Create ER Diagram:** Run the Mermaid code in `DATABASE.md` to ensure it renders (Mermaid preview).
12. **Commit Docs:** Update `DATABASE.md` with explanations. Use markdown headings, bullet lists as above. Preview in GitHub to check formatting.
13. **Review:** Ensure all citation links in docs are correct (if manual copy).
14. **Finalize:** `git add` and `git commit` all changes with a message like `"docs: add database schema and models"`.
15. **Push & PR:** Push branch and open a Pull Request for review, or merge to main if working solo.

This completes the database implementation phase for Kontexa. Following these deliverables, an AI agent or developer has a clear, step-by-step blueprint to set up and validate the database layer with professional standards and scalability. 
