# Security Architecture & Threat Model

Security is an essential requirement for Kontexa. Because the platform connects to developer codebases, documentation, communication channels, and external APIs, strict boundaries are enforced at every level of the stack.

---

## 1. Threat Model & Key Attack Vectors

| Attack Vector | Threat Scenario | Mitigation Strategy |
| :--- | :--- | :--- |
| **Cross-Tenant Data Leakage** | Tenant A queries API with Tenant B's workspace or project ID (IDOR). | Strict backend membership checks on every query (`workspace_id` scoping); automated cross-tenant rejection tests. |
| **Credential / Token Exposure** | GitHub OAuth tokens, LLM API keys, or DB credentials leak in logs, client bundles, or commits. | Credentials kept strictly server-side; zero `NEXT_PUBLIC_` secrets; token encryption at rest using AES-256-GCM; structured log redaction. |
| **Prompt Injection** | Malicious content in repository files, issues, or emails overrides agent instructions. | Retrieved text treated as untrusted data; isolated system prompt boundaries; write actions default to disabled without explicit human approval. |
| **SQL Injection** | Attacker injects malicious SQL via user inputs or search queries. | 100% parameterized queries via SQLAlchemy 2.0 ORM; zero raw SQL string concatenation. |
| **Arbitrary Code Execution** | Agent task execution escapes sandbox and compromises host system. | Containerized, resource-limited execution sandboxes; no root access; restricted network egress; path traversal validation. |
| **Unauthorized Write Actions** | Agent executes hallucinated or unintended modifications (merges, deletes). | Immutable plan hash generation; explicit human-in-the-loop confirmation required for all write operations. |

---

## 2. Multi-Tenant Isolation Architecture

1. **Explicit Scoping**:
   - Every tenant-owned row in the database includes a `workspace_id` foreign key.
   - Database queries must explicitly filter on `workspace_id` matching the authenticated user's verified membership.
2. **Backend Enforcement**:
   - Authorization is enforced by backend FastAPI dependencies.
   - Frontend route hiding or navigation guards are treated purely as UX enhancements, never security controls.
3. **Audit Trail**:
   - The `audit_logs` table records every critical event (authentication, membership changes, integration setup, tool execution) with `workspace_id`, `user_id`, IP address, and timestamp.

---

## 3. Secret Management & Cryptography

- **Environment Variables**: Managed via Pydantic Settings (`kontexa.core.config.Settings`). Sensitive values are loaded from `.env` or system environment and never hardcoded.
- **Password Hashing**: Implemented using PBKDF2-HMAC-SHA256 with 600,000 iterations (OWASP recommendation) and unique 16-byte cryptographically secure salts.
- **Session Tokens & Cookies**:
  - Session tokens are generated with 32 bytes of cryptographic entropy (`secrets.token_urlsafe(32)`).
  - Only the SHA-256 digest (`token_hash`) is stored in the database `user_sessions` table.
  - Session cookies are set with `HttpOnly=True`, `SameSite=Lax` (or `Strict`), `Secure=True` in production, and scoped to API endpoints.
  - Tokens are never stored in browser `localStorage`.
- **CSRF Protection**:
  - State-modifying endpoints (`/logout` and future mutations) require an `X-CSRF-Token` header.
  - CSRF tokens are signed HMAC-SHA256 digests encoding the user ID, session token hash, and expiry timestamp, validated on the backend.
- **TLS/SSL Encryption**:
  - Connections to PostgreSQL require TLS (`DATABASE_SSL_MODE=require` for Aiven).
  - External API calls (AI providers, GitHub) use HTTPS with strict certificate validation.
- **Token Encryption at Rest**:
  - In Sprint 06/24, OAuth access/refresh tokens in `integrations.auth_data` will be encrypted using AES-256-GCM envelope encryption before persistence.

---

## 4. Prompt Injection Defense

All content fetched from external sources (code files, commit messages, PR reviews, documentation chunks, Slack threads) is classified as **Untrusted External Data**:
- Retrieved context is wrapped in clear contextual data delimiters when passed to the LLM.
- System prompts explicitly instruct models that retrieved text must never be interpreted as commands or policy overrides.
- Critical actions (file creation, git push, PR creation) cannot be triggered directly by LLM text output; they require structured tool calls validated against JSON schemas and approved by the developer.

---

## 5. Human-in-the-Loop Approval Safeguards

- Agent task workflows are split into two distinct phases: **Planning** and **Execution**.
- During Planning, the agent generates an execution manifest (diff, file targets, shell commands).
- Kontexa computes a SHA-256 cryptographic hash of the manifest (`plan_hash`).
- Execution is locked until the developer submits an approval token matching the exact `plan_hash`.
- Any mutation of the plan invalidates the approval token.
- Automatic merging of pull requests is strictly prohibited.
