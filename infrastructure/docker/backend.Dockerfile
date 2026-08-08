# Python 3.12+ backend Dockerfile using uv for dependency management
FROM python:3.12-slim AS base

# Install uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:0.12.1 /uv /uvx /bin/

WORKDIR /app

# Enable bytecode compilation and copy environment mode
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1

# Copy dependency manifests
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./backend/
WORKDIR /app/backend

# Sync dependencies without project root installation
RUN uv sync --frozen --no-install-project

# Copy backend source code
COPY backend/src ./src
COPY backend/migrations ./migrations
COPY backend/alembic.ini ./

# Sync project root
RUN uv sync --frozen

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "kontexa.main:app", "--host", "0.0.0.0", "--port", "8000"]
