# Configuration Reference

Configuration in Kontexa is managed per execution context. Example files are provided as templates; never commit sensitive values.

---

## 1. Environment Configuration Files

- Root `.env.example`: Template for Docker Compose variable substitution.
- Backend `backend/.env.example`: Template for local FastAPI backend execution.
- Frontend `frontend/.env.example`: Template for Next.js web application.

---

## 2. Backend Configuration (`backend/.env`)

Managed via `kontexa.core.config.Settings` using Pydantic Settings:

| Variable | Type | Default | Required | Description |
| :--- | :--- | :--- | :---: | :--- |
| `APP_NAME` | `str` | `"Kontexa Backend"` | No | Human-readable application identifier. |
| `APP_VERSION` | `str` | `"0.1.0"` | No | Deployed application version. |
| `APP_ENV` | `str` | `"development"` | No | Execution environment (`development`, `staging`, `production`). |
| `DEBUG` | `bool` | `false` | No | Debug mode toggle (enables SQLAlchemy echo). |
| `LOG_LEVEL` | `str` | `"INFO"` | No | Logging severity level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `HOST` | `str` | `"0.0.0.0"` | No | Server network bind address. |
| `PORT` | `int` | `8000` | No | Server network bind port. |
| `DATABASE_URL` | `str` | None | **Yes** | Async SQLAlchemy PostgreSQL connection string (e.g. `postgresql+asyncpg://user:pass@host:5432/db`). |
| `DATABASE_POOL_SIZE` | `int` | `5` | No | SQLAlchemy connection pool size (kept low for cloud free-tiers). |
| `DATABASE_MAX_OVERFLOW` | `int` | `10` | No | Max overflow connections beyond pool size. |
| `DATABASE_CA_CERT` | `str` | `None` | No | Path to CA certificate file for TLS validation (e.g. Aiven). |
| `DATABASE_SSL_MODE` | `str` | `"disable"` | No | SSL mode for PostgreSQL (`disable` or `require`). |
| `REDIS_URL` | `str` | `"redis://localhost:6379/0"` | No | Redis connection string. |
| `HEALTH_CHECK_TIMEOUT_SECONDS` | `float` | `2.0` | No | Maximum time allowed per dependency check before reporting degraded status. |
| `CORS_ORIGINS` | `list[str]` | `["http://localhost:3000"]` | No | JSON list of trusted browser origin URLs allowed for CORS. |

---

## 3. Frontend Configuration (`frontend/.env.local`)

| Variable | Type | Default | Required | Description |
| :--- | :--- | :--- | :---: | :--- |
| `BACKEND_URL` | `str` | `"http://localhost:8000"` | No | Internal destination for Next.js `/api/:path*` proxy rewrite. Set to `http://backend:8000` in Docker Compose. |

*Note: No `NEXT_PUBLIC_*` variables are currently defined. Never expose credentials to browser bundles.*

---

## 4. Docker Compose Environment

`infrastructure/docker/docker-compose.yml` uses the following environment variables:
- `POSTGRES_USER` (default: `kontexa`)
- `POSTGRES_PASSWORD` (default: `kontexa_pass`)
- `POSTGRES_DB` (default: `kontexa_db`)
- `APP_VERSION` (default: `0.1.0`)
- `HEALTH_CHECK_TIMEOUT_SECONDS` (default: `2`)
