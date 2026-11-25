# API Specification & System Contracts

**API Version**: `v1`  
**Base URL**: `/api/v1`  
**Protocol**: HTTPS (TLS 1.3) / HTTP/2  
**Source of Truth**: [docs/README.md](README.md) · [docs/ARCHITECTURE.md](ARCHITECTURE.md) · [docs/FEATURE_STATUS.md](FEATURE_STATUS.md)

---

## 1. API Architecture & Standards

Kontexa exposes a RESTful HTTP API built with FastAPI. All public endpoints adhere to the following standards:

- **JSON Payload Format**: Request and response bodies are strictly formatted JSON validated against Pydantic schemas.
- **Request Correlation**: Clients can optionally supply `X-Request-ID`. If absent, the API gateway generates a UUID4 `X-Request-ID` and echoes it in all response headers and structured logs.
- **HTTP Status Codes**:
  - `200 OK`: Request succeeded.
  - `201 Created`: Resource successfully created.
  - `400 Bad Request`: Validation failure on request body, parameters, or invalid plan hash.
  - `401 Unauthorized`: Authentication missing, expired, or invalid session cookie.
  - `403 Forbidden`: Authenticated user lacks permission for the requested workspace/resource.
  - `404 Not Found`: Resource does not exist or user lacks access (prevents existence probing).
  - `422 Unprocessable Entity`: Pydantic schema validation failure.
  - `503 Service Unavailable`: Required backend dependency (PostgreSQL or Redis) is degraded.
- **Standard Error Payload**:
  All non-2xx responses return a structured error response:
  ```json
  {
    "detail": "Descriptive, client-safe error message",
    "code": "ERROR_CODE_IDENTIFIER",
    "request_id": "c1f72a9e-8b20-4e3d-b4f1-9d8a21f73e44"
  }
  ```

---

## 2. Active Implemented Endpoints

### `GET /live` & `GET /api/v1/live`

Fast process-level liveness probe returning `200 OK` without querying external databases or caches. Used by Kubernetes/ECS liveness probes.

- **URL**: `/live` or `/api/v1/live`
- **Method**: `GET`
- **Authentication**: None
- **Response Headers**: `Content-Type: application/json`, `X-Request-ID: <uuid>`

#### Successful Response (`200 OK`)
```json
{
  "status": "ok",
  "service": "kontexa",
  "version": "0.1.0"
}
```

---

### `GET /ready` & `GET /api/v1/ready` / `GET /health` & `GET /api/v1/health`

Reports application readiness by concurrently probing PostgreSQL and Redis dependencies. Used by orchestrator readiness probes to gate inbound traffic.

- **URL**: `/ready`, `/api/v1/ready`, `/health`, or `/api/v1/health`
- **Method**: `GET`
- **Authentication**: None (Public readiness probe)
- **Response Headers**: `Content-Type: application/json`, `X-Request-ID: <uuid>`

#### Successful Response (`200 OK`)
```json
{
  "status": "ok",
  "service": "kontexa",
  "environment": "development",
  "version": "0.1.0",
  "timestamp": "2026-11-25T00:20:00.000000Z",
  "dependencies": {
    "database": {
      "status": "ok",
      "latency_ms": 1.25
    },
    "redis": {
      "status": "ok",
      "latency_ms": 0.45
    }
  }
}
```

#### Degraded Response (`503 Service Unavailable`)
```json
{
  "status": "degraded",
  "service": "kontexa",
  "environment": "development",
  "version": "0.1.0",
  "timestamp": "2026-11-25T00:20:00.000000Z",
  "dependencies": {
    "database": {
      "status": "ok",
      "latency_ms": 1.30
    },
    "redis": {
      "status": "unavailable",
      "latency_ms": 0.0
    }
  }
}
```

---

### `POST /api/v1/auth/register`
Creates a new user account.
- **URL**: `/api/v1/auth/register` or `/auth/register`
- **Method**: `POST`
- **Authentication**: None
- **Request Body**:
  ```json
  {
    "email": "developer@example.com",
    "password": "SecurePassword123!",
    "name": "Jane Developer"
  }
  ```
- **Response (`201 Created`)**:
  ```json
  {
    "id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
    "email": "developer@example.com",
    "name": "Jane Developer",
    "is_active": true,
    "created_at": "2026-11-25T01:00:00Z"
  }
  ```

---

### `POST /api/v1/auth/login`
Authenticates a user and sets an HttpOnly session cookie.
- **URL**: `/api/v1/auth/login` or `/auth/login`
- **Method**: `POST`
- **Authentication**: None
- **Request Body**:
  ```json
  {
    "email": "developer@example.com",
    "password": "SecurePassword123!"
  }
  ```
- **Response Headers**:
  ```text
  Set-Cookie: kontexa_session=sess_9f8e7d...; Path=/; HttpOnly; SameSite=lax; Max-Age=2592000
  ```
- **Response (`200 OK`)**:
  ```json
  {
    "user": {
      "id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
      "email": "developer@example.com",
      "name": "Jane Developer",
      "is_active": true,
      "created_at": "2026-11-25T01:00:00Z"
    },
    "csrf_token": "csrf_payload.signature"
  }
  ```

---

### `POST /api/v1/auth/logout`
Revokes the current session and clears the session cookie.
- **URL**: `/api/v1/auth/logout` or `/auth/logout`
- **Method**: `POST`
- **Authentication**: Valid session cookie + `X-CSRF-Token` header
- **Response Headers**:
  ```text
  Set-Cookie: kontexa_session=; Path=/; Max-Age=0
  ```
- **Response (`200 OK`)**:
  ```json
  {
    "status": "ok",
    "message": "Logged out successfully"
  }
  ```

---

### `GET /api/v1/auth/me`
Fetches the current authenticated user context and workspace memberships.
- **URL**: `/api/v1/auth/me` or `/auth/me`
- **Method**: `GET`
- **Authentication**: Valid session cookie
- **Response (`200 OK`)**:
  ```json
  {
    "id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
    "email": "developer@example.com",
    "name": "Jane Developer",
    "is_active": true,
    "created_at": "2026-11-25T01:00:00Z",
    "workspaces": [
      {
        "workspace_id": "w1x2y3z4-a5b6-7c8d-9e0f-1a2b3c4d5e6f",
        "name": "Acme Engineering",
        "slug": "acme-eng",
        "role": "admin"
      }
    ]
  }
  ```

---

### `GET /api/v1/auth/csrf`
Generates a signed HMAC-SHA256 CSRF token for the authenticated session.
- **URL**: `/api/v1/auth/csrf` or `/auth/csrf`
- **Method**: `GET`
- **Authentication**: Valid session cookie
- **Response (`200 OK`)**:
  ```json
  {
    "csrf_token": "csrf_payload.signature"
  }
  ```

---

### `GET /api/v1/workspaces`
List all workspaces where the authenticated user is an active member.
- **URL**: `/api/v1/workspaces` or `/workspaces`
- **Method**: `GET`
- **Authentication**: Valid session cookie
- **Response (`200 OK`)**: List of `WorkspaceDetailResponse` items.

---

### `POST /api/v1/workspaces`
Create a new workspace; designates caller as `owner`.
- **URL**: `/api/v1/workspaces` or `/workspaces`
- **Method**: `POST`
- **Authentication**: Valid session cookie + `X-CSRF-Token` header
- **Request Body**: `{"name": "string", "slug": "optional-slug"}`
- **Response (`201 Created`)**: `WorkspaceResponse`.

---

### `GET /api/v1/workspaces/{workspace_id}`
Get workspace details and caller's verified role.
- **URL**: `/api/v1/workspaces/{workspace_id}`
- **Method**: `GET`
- **Authentication**: Valid session cookie (caller must be a member; returns 404 on cross-tenant access)

---

### `PATCH /api/v1/workspaces/{workspace_id}`
Update workspace settings (name, slug). Requires `admin` or `owner` role.
- **URL**: `/api/v1/workspaces/{workspace_id}`
- **Method**: `PATCH`
- **Authentication**: Valid session cookie + `X-CSRF-Token` header

---

### `DELETE /api/v1/workspaces/{workspace_id}`
Soft-deletes a workspace. Only the `owner` can delete.
- **URL**: `/api/v1/workspaces/{workspace_id}`
- **Method**: `DELETE`
- **Authentication**: Valid session cookie + `X-CSRF-Token` header

---

### `GET /api/v1/workspaces/{workspace_id}/members`
List members in the workspace. Requires `viewer` role or above.
- **URL**: `/api/v1/workspaces/{workspace_id}/members`
- **Method**: `GET`
- **Authentication**: Valid session cookie

---

### `POST /api/v1/workspaces/{workspace_id}/members`
Add a member by email to the workspace. Requires `admin` or `owner` role.
- **URL**: `/api/v1/workspaces/{workspace_id}/members`
- **Method**: `POST`
- **Authentication**: Valid session cookie + `X-CSRF-Token` header
- **Request Body**: `{"email": "string", "role": "member"}`

---

### `GET /api/v1/workspaces/{workspace_id}/projects`
List projects scoped to the workspace.
- **URL**: `/api/v1/workspaces/{workspace_id}/projects`
- **Method**: `GET`
- **Authentication**: Valid session cookie (caller must be a member)

---

### `POST /api/v1/workspaces/{workspace_id}/projects`
Create a new project in the workspace. Requires `member` or above.
- **URL**: `/api/v1/workspaces/{workspace_id}/projects`
- **Method**: `POST`
- **Authentication**: Valid session cookie + `X-CSRF-Token` header
- **Request Body**: `{"name": "string", "slug": "optional-slug", "description": "optional"}`

---

### `GET /api/v1/workspaces/{workspace_id}/projects/{project_id}`
Get project details ensuring strict workspace tenancy.
- **URL**: `/api/v1/workspaces/{workspace_id}/projects/{project_id}`
- **Method**: `GET`
- **Authentication**: Valid session cookie (caller must belong to `workspace_id`)

---

## 3. Planned Target Contracts (Sprint 09–28)

### 3.1 Conversational AI & Message Contracts (`/api/v1/conversations`)

---

### 3.2 Conversational Chat & SSE Streaming Contract

#### `POST /api/v1/conversations/{conv_id}/messages`
Appends a message to a conversation thread and streams the assistant's answer via Server-Sent Events.

- **Query Parameters**: `stream=true` (defaults to true)
- **Request Headers**: `Accept: text/event-stream`
- **Request Body**:
  ```json
  {
    "content": "Where is the database pool size configured in this repo?",
    "include_retrieval": true
  }
  ```
- **Response Headers**:
  ```text
  Content-Type: text/event-stream; charset=utf-8
  Cache-Control: no-cache
  Connection: keep-alive
  X-Accel-Buffering: no
  ```
- **Stream Event Sequence**:
  ```text
  event: token
  data: {"delta": "The database pool size is configured in "}

  event: token
  data: {"delta": "backend/src/kontexa/core/config.py."}

  event: citation
  data: {"id": "cit_1", "type": "code", "path": "backend/src/kontexa/core/config.py", "lines": [33, 40], "commit": "d0b10fb"}

  event: usage
  data: {"prompt_tokens": 128, "completion_tokens": 42, "model": "claude-3-5-sonnet", "cost_usd": 0.0008}

  event: done
  data: [DONE]
  ```

---

### 3.3 Gated Agent Task Planning & Execution Contract

#### `POST /api/v1/projects/{proj_id}/tasks/plan`
Generates a structured, immutable execution manifest with file diffs and command actions.

- **Request Body**:
  ```json
  {
    "prompt": "Add a unit test verifying 503 response on database timeout in health check",
    "target_paths": ["backend/tests/unit/test_health.py"]
  }
  ```
- **Response (`201 Created`)**:
  ```json
  {
    "task_id": "tsk_4a8b1c2d",
    "status": "awaiting_approval",
    "plan_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "manifest": {
      "file_diffs": [
        {
          "path": "backend/tests/unit/test_health.py",
          "hunk": "@@ -80,3 +80,18 @@ async def test_api_v1_health_check..."
        }
      ],
      "verification_commands": ["uv run pytest backend/tests/unit/test_health.py"]
    },
    "created_at": "2026-11-25T01:05:00Z"
  }
  ```

#### `POST /api/v1/tasks/{task_id}/execute`
Executes an approved plan in an isolated sandbox. Fails if `approved_plan_hash` does not strictly match `plan_hash`.

- **Request Body**:
  ```json
  {
    "approved_plan_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  }
  ```
- **Response (`200 OK`)**:
  ```json
  {
    "task_id": "tsk_4a8b1c2d",
    "status": "verification_passed",
    "test_output": "================ 1 passed in 0.42s ================",
    "can_create_draft_pr": true
  }
  ```

#### `POST /api/v1/tasks/{task_id}/push`
Pushes a git branch and opens a GitHub Draft Pull Request.
- **Request Body**:
  ```json
  {
    "pr_title": "test: add timeout test for health check endpoint",
    "pr_body": "Automated verification passed in sandbox: 1 passed in 0.42s."
  }
  ```
- **Response (`200 OK`)**:
  ```json
  {
    "task_id": "tsk_4a8b1c2d",
    "status": "pr_created",
    "branch": "kontexa/task-4a8b1c2d",
    "draft_pr_url": "https://github.com/Raj-Patel7807/kontexa/pull/42",
    "draft_pr_number": 42
  }
  ```
