# Configuration Reference

Configuration is intentionally split by execution context. Copy example files only as a starting
point; never commit secrets. The backend loads `.env` from its working directory, and Next.js loads
environment files from `frontend/`.

## Root `.env.example`

The root example provides shared local values. Docker Compose automatically reads a root `.env` for
variable substitution, but the current Compose file uses only `APP_VERSION` and
`HEALTH_CHECK_TIMEOUT_SECONDS` from this example. Its PostgreSQL variables have compose defaults.
When running the backend from `backend/`, use `backend/.env`; the backend does not load the root
file.

| Variable | Component | Required | Example / behavior |
| --- | --- | --- | --- |
| `APP_ENV` | shared template | No | `development`; Compose pins backend to `development`. |
| `APP_VERSION` | Compose backend | No | `0.1.0` when omitted. |
| `DATABASE_URL` | shared template | No direct consumer today | Local async SQLAlchemy URL; set it in `backend/.env` for local backend execution. |
| `REDIS_URL` | shared template | No direct consumer today | Local Redis URL; set it in `backend/.env` for local backend execution. |
| `HEALTH_CHECK_TIMEOUT_SECONDS` | Compose backend | No | Seconds allowed for a dependency readiness probe; default `2`. |
| `FRONTEND_URL` | shared template | No direct consumer today | `http://localhost:3000`. |
| `BACKEND_URL` | shared template | No direct consumer today | `http://localhost:8000`; frontend uses its own file. |
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` | commented placeholders | No | No AI-provider code reads these yet. Do not add real keys to example files. |

## Backend `backend/.env.example`

`kontexa.core.config.Settings` validates these settings. `DATABASE_URL` is required by the settings
model and is commented out in the example, so uncomment or add it before starting a local backend.

| Variable | Required | Development behavior | Production consideration |
| --- | --- | --- | --- |
| `APP_ENV` | No | Defaults to `development`. | Set an environment-appropriate label. |
| `APP_VERSION` | No | Defaults to `0.1.0`. | Supply the deployed version if needed. |
| `DEBUG` | No | Enables SQLAlchemy echo when true; example is `true`. | Keep false unless diagnostic output is intended. |
| `LOG_LEVEL` | No | Python logging level; default `INFO`. | Set the desired operational level. |
| `HOST` | No | Default bind address is `0.0.0.0`. | Bind according to the deployment network. |
| `PORT` | No | Default `8000`. | Match the hosting/runtime port contract. |
| `DATABASE_URL` | Yes | Use `postgresql+asyncpg://…`; local example targets `localhost:5432/kontexa_db`. | Use the managed database URL; Alembic derives a synchronous psycopg2 URL for offline migrations. |
| `DATABASE_CA_CERT` | No | Empty means no custom CA context. | Absolute CA-certificate path for a TLS database such as Aiven. |
| `DATABASE_SSL_MODE` | No | `disable` gives asyncpg no SSL arguments. | `require` enables TLS; a configured CA file is used when available. |
| `DATABASE_POOL_SIZE` | No | Default `5`. | Tune for database connection limits. |
| `DATABASE_MAX_OVERFLOW` | No | Default `10`. | Tune together with pool size. |
| `REDIS_URL` | No | Defaults to `redis://localhost:6379/0`. | Use the managed Redis endpoint if Redis remains required. |
| `HEALTH_CHECK_TIMEOUT_SECONDS` | No | Default `2`; must be positive. | Set to a dependency-appropriate timeout. |
| `CORS_ORIGINS` | No | JSON list, default `["http://localhost:3000"]`. | Restrict to trusted browser origins. |

## Frontend `frontend/.env.example`

| Variable | Required | Behavior |
| --- | --- | --- |
| `BACKEND_URL` | No | Server-side target for the Next.js `/api/:path*` rewrite; defaults to `http://localhost:8000`. In Docker Compose it is set to `http://backend:8000`. |

No `NEXT_PUBLIC_*` variables are configured. Keep backend and provider credentials server-side.

## Docker Compose configuration

`infrastructure/docker/docker-compose.yml` creates PostgreSQL 16 with pgvector, Redis 7, backend,
and frontend services. It supplies internal backend URLs directly and uses these optional root
environment variables: `POSTGRES_USER` (default `kontexa`), `POSTGRES_PASSWORD` (default
`kontexa_pass`), `POSTGRES_DB` (default `kontexa_db`), `APP_VERSION`, and
`HEALTH_CHECK_TIMEOUT_SECONDS`. Default credentials are suitable only for local development.
