# API Specification & Conventions

## 1. API Architecture & Standards

Kontexa exposes a RESTful HTTP API built with FastAPI. All public endpoints adhere to the following standards:

- **JSON Payload Format**: Request and response bodies are strictly formatted JSON validated against Pydantic schemas.
- **HTTP Status Codes**: Standard REST semantics:
  - `200 OK`: Request succeeded.
  - `201 Created`: Resource successfully created.
  - `400 Bad Request`: Validation failure on request body or parameters.
  - `401 Unauthorized`: Authentication missing or invalid.
  - `403 Forbidden`: Authenticated user lacks permission for the requested workspace/resource.
  - `404 Not Found`: Resource does not exist or user lacks access.
  - `503 Service Unavailable`: Required backend dependency (PostgreSQL or Redis) is degraded.
- **Error Payloads**: All non-2xx responses provide structured error objects:
  ```json
  {
    "detail": "Descriptive error message"
  }
  ```
- **OpenAPI / Swagger Documentation**: Available at runtime at `/docs` (Swagger UI) and `/redoc` (ReDoc) when running the backend locally.

---

## 2. Implemented Endpoints (Sprint 01)

### `GET /health` & `GET /api/v1/health`

Reports application readiness by concurrently probing PostgreSQL and Redis dependencies.

- **URL**: `/health` or `/api/v1/health`
- **Method**: `GET`
- **Authentication**: None (Public readiness probe)
- **Response Headers**: `Content-Type: application/json`

#### Successful Response (`200 OK`)
Returned when both PostgreSQL and Redis respond within the configured timeout (`HEALTH_CHECK_TIMEOUT_SECONDS`, default 2.0s):

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
Returned when either PostgreSQL or Redis fails to respond, times out, or throws an error:

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

*Note: Raw connection strings, hostnames, and internal exception traces are stripped from the response and logged server-side.*

---

## 3. Planned Endpoints Roadmap

The following endpoint groups are designed for upcoming sprints:

| Group | Method | Path | Planned Sprint |
| :--- | :--- | :--- | :---: |
| **Auth** | `POST` | `/api/v1/auth/register` | Sprint 07 |
| **Auth** | `POST` | `/api/v1/auth/login` | Sprint 07 |
| **Auth** | `POST` | `/api/v1/auth/logout` | Sprint 07 |
| **Auth** | `GET` | `/api/v1/auth/me` | Sprint 07 |
| **Workspaces** | `GET`, `POST` | `/api/v1/workspaces` | Sprint 08 |
| **Projects** | `GET`, `POST` | `/api/v1/workspaces/{ws_id}/projects` | Sprint 08 |
| **Chat** | `GET`, `POST` | `/api/v1/projects/{proj_id}/conversations` | Sprint 10 |
| **Chat** | `POST` | `/api/v1/conversations/{conv_id}/messages` (SSE streaming) | Sprint 12 |
| **Knowledge** | `POST` | `/api/v1/projects/{proj_id}/documents` (Upload) | Sprint 13 |
| **Knowledge** | `POST` | `/api/v1/projects/{proj_id}/retrieval` (Query) | Sprint 14 |
| **GitHub** | `POST` | `/api/v1/integrations/github/connect` | Sprint 15 |
| **Tasks** | `POST` | `/api/v1/projects/{proj_id}/tasks/plan` | Sprint 19 |
| **Tasks** | `POST` | `/api/v1/tasks/{task_id}/execute` (Hash-bound approval) | Sprint 20 |
