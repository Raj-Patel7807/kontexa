# Security Policy

## Reporting Security Vulnerabilities

We take the security of Kontexa seriously. If you discover a security vulnerability, please do **NOT** open a public GitHub issue.

Instead, please send a responsible disclosure report to the repository maintainer:
- **Email**: `rajpatel7807@gmail.com`
- Please include a detailed description of the vulnerability, steps to reproduce, affected components, and potential impact.
- You should receive an acknowledgment within 48 hours.

---

## Security Principles & Boundaries

Kontexa enforces the following security boundaries across all engineering work:

1. **Strict Multi-Tenant Isolation**:
   - Every tenant-owned row in the database must be scoped to a `workspace_id`.
   - Access control must be validated at the backend API layer before data is fetched or returned.
   - Cross-workspace data leakage is treated as a critical security defect.

2. **Least Privilege & Secret Protection**:
   - OAuth tokens, LLM API keys, database credentials, and signing secrets must never enter client bundles, logs, or commit history.
   - Provider access tokens must be encrypted at rest.
   - Integration scopes must request the minimum necessary permissions.

3. **Untrusted Data & Prompt Injection Defense**:
   - All retrieved context (repository files, issue descriptions, user emails, external docs) is treated as untrusted data.
   - Prompt injections present in retrieved data must never override system prompts or tool policies.
   - Strict input validation is enforced at all API boundaries using Pydantic schemas.

4. **Human-in-the-Loop for Write Operations**:
   - By default, all AI agents and tools operate in read-only mode.
   - Any mutating or external action (modifying files, pushing branches, creating draft pull requests, sending external messages) requires explicit human confirmation.
   - Action approvals are cryptographically bound to an immutable plan hash.

5. **Sandbox Isolation for Code Execution**:
   - Agent workspace execution and testing must be sandboxed to prevent filesystem traversal, symlink escape, shell injection, or access to host secrets.
   - Subprocesses must use safe parameterized argument lists rather than shell string execution.

For detailed security threat modeling, see [docs/SECURITY.md](docs/SECURITY.md).
