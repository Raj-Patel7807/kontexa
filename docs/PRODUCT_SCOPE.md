# Product Scope & Release Definition

**Document Purpose**: Definitive scope boundary, acceptance criteria, and release definition for Kontexa First Release (MVP).  
**Source of Truth**: [docs/PRD.md](PRD.md) · [docs/ROADMAP.md](ROADMAP.md) · [docs/FEATURE_STATUS.md](FEATURE_STATUS.md)

---

## 1. Product in One Sentence

Kontexa is an **AI Software Engineering Workspace** that connects a developer's chosen engineering tools, understands relationships across their code, documentation, and issues, and helps them investigate and perform engineering work with verifiable citations and human control.

---

## 2. Release Scope Boundaries: First Release (MVP) vs. Deferred

| Capability Area | Included in First Release (MVP) | Explicitly Deferred to Later Phases |
| :--- | :--- | :--- |
| **Identity & Access** | Email/password authentication, session management, workspaces, projects, RBAC (`Owner`, `Admin`, `Member`, `Viewer`). | Enterprise SAML/SSO, multi-factor authentication (MFA), SCIM provisioning. |
| **Conversational AI** | Persistent conversation threads, multipart messages, markdown rendering, SSE token streaming, provider abstraction. | Voice chat, multi-agent autonomous chatrooms, fine-tuned custom foundation models. |
| **Knowledge Engine** | Manual document upload (Markdown, PDF, TXT), SHA256 content deduplication, chunking, pgvector similarity search, line citations. | OCR extraction on complex scanned diagrams, multi-modal video/audio processing. |
| **VCS Connector** | Deep GitHub App integration (repo tree sync, AST symbol parsing, commit history, branch creation, Draft PRs). | GitLab, Bitbucket, Azure DevOps, self-hosted Perforce/Gerrit instances. |
| **Secondary Connector** | Exactly one secondary engineering connector (Linear or Jira) demonstrating cross-source context correlation. | Slack, Discord, Microsoft Teams, Notion, Confluence, Gmail, Outlook, Sentry, Datadog. |
| **Agent Tasks** | Read-only analysis by default; plan generation with SHA-256 approval binding; sandboxed test execution; human-approved Draft PR creation. | Unrestricted shell execution, direct pushing to `main`, automatic PR merging, production deployments. |
| **Architecture** | Single-unit FastAPI modular monolith, PostgreSQL 16 with pgvector, Redis cache, Next.js 16 App Router. | Microservices decomposition, Kubernetes cluster orchestration, multi-region database sharding. |
| **Developer Tools** | Web application dashboard, GitHub pull request links, structured investigation workflows (`Explain Code`, `Investigate Bug`). | Standalone desktop application, VS Code extension suite, JetBrains IDE plugins. |

---

## 3. First-Release Acceptance Checklist

Every capability must be verified against this checklist before MVP release sign-off:

### A. Authentication & Tenancy
- [ ] User sign-up, login, and session invalidation work end-to-end.
- [ ] User sessions are secured with HttpOnly, SameSite cookies.
- [ ] Workspace creation, invitation, and role assignment (`Owner`, `Admin`, `Member`, `Viewer`) are enforced.
- [ ] Automated integration tests verify that cross-workspace access attempts return HTTP 403 Forbidden (zero IDOR vulnerabilities).
- [ ] Projects are strictly scoped within workspaces; database foreign keys prevent cross-tenant project assignment.

### B. Chat & AI Gateway
- [ ] Conversations and multipart messages persist to PostgreSQL.
- [ ] Server-Sent Events (SSE) stream tokens to the frontend in real time with smooth progressive rendering.
- [ ] Client cancellation immediately terminates upstream LLM token generation.
- [ ] AI gateway allows switching between OpenAI, Anthropic, Gemini, and a deterministic local `mock` provider via configuration.
- [ ] Automated tests verify token usage accounting and estimated cost tracking.

### C. Knowledge Ingestion & Retrieval
- [ ] Document upload validates file types, size limits, and computes SHA-256 content hashes.
- [ ] Sliding-window chunker preserves paragraph boundaries and emits metadata (`document_id`, `version`, `chunk_index`).
- [ ] `pgvector` similarity search filters strictly by active workspace and project.
- [ ] Chat answers cite source documents with clickable badges that display the referenced section.

### D. GitHub Repository Intelligence
- [ ] GitHub App installation flow links specific repositories to a project.
- [ ] Synchronization engine pulls repository file trees and commits while respecting `.gitignore`.
- [ ] Language-aware AST parser extracts symbols (functions, classes, imports) for Python and TypeScript files.
- [ ] Codebase Q&A answers queries with exact file paths, line ranges, and commit SHAs (e.g. `src/auth.py#L40-L65`).

### E. Gated Development Tasks & Sandbox Execution
- [ ] Agent generates an immutable execution manifest with file diffs and command targets.
- [ ] Plan approval is cryptographically bound to `SHA256(manifest)`. Execution is rejected if the plan hash does not match.
- [ ] File modifications and test runs (`uv run pytest`) execute in an isolated sandbox environment with CPU and memory limits.
- [ ] The agent presents test results and diffs to the developer for final review.
- [ ] The agent creates a GitHub **Draft PR** only after explicit user approval. Autonomous merge is technically disabled.

### F. Secondary Connector & Cross-Source Correlation
- [ ] Connects to Linear or Jira to pull issues and acceptance criteria.
- [ ] Demonstrates at least one cross-source query linking a GitHub commit/PR to a tracking ticket with verified permissions.

### G. Operational Reliability & Security
- [ ] All OAuth tokens and provider API keys are encrypted at rest with AES-256-GCM.
- [ ] Zero secrets or API keys are exposed to client-side bundles or logged in application traces.
- [ ] Public readiness endpoints (`/health`, `/api/v1/health`) return 503 on dependency failure without leaking internal credentials.
- [ ] GitHub Actions CI runs clean for backend lint/format/tests, frontend lint/typecheck/build, and Docker Compose integration smoke tests.
- [ ] Complete documentation is synchronized with actual code; zero planned features are labeled as implemented.

---

## 4. Definition of Done (DoD) for Product Features

A feature is considered **Done** and eligible to be labeled **`Implemented`** only when:

1. **User Reachability**: A user can reach and execute the capability through the user interface or active, authenticated API endpoints.
2. **Backend Enforcement**: Authorization and tenant scoping are validated at the API boundary; frontend hiding alone is insufficient.
3. **Persistence & Data Integrity**: Data is stored in relational tables using Alembic migrations; failure modes (rollbacks, timeouts) are handled.
4. **Automated Test Coverage**:
   - Backend domain logic is covered by passing unit and integration tests in pytest.
   - Frontend UI is typechecked (`tsc --noEmit`) and linted (`eslint`).
   - Happy paths, permission denial paths, and edge cases are verified.
5. **UI States**: The web interface implements explicit **Loading**, **Empty**, **Error**, and **Success** states. No fake buttons or mock placeholders presented as real.
6. **Documentation Synchronization**: [docs/FEATURE_STATUS.md](FEATURE_STATUS.md) and related architecture docs are updated in the same sprint.
7. **Passing CI**: All GitHub Actions workflows pass without warnings or skipped errors.

---

## 5. Technical Limits & Operational Thresholds

- **Maximum Document Upload Size**: 25 MB per document.
- **Maximum Repository Size (Initial Sync)**: 500 MB / 50,000 files.
- **Chunk Size**: 500 tokens with 50-token overlap.
- **Embedding Dimension**: 1536 dimensions (OpenAI text-embedding-3-small compatible).
- **Readiness Check Timeout**: 2.0 seconds per dependency.
- **Sandbox Execution Timeout**: 120 seconds per test run.
- **Sandbox Memory Limit**: 2048 MB RAM ceiling.
