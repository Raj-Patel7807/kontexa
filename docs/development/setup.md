# Local Development Setup

This guide details how to set up, build, and run Kontexa on your local development machine.

---

## 1. Prerequisites

- **Python 3.12+** and [`uv`](https://docs.astral.sh/uv/) (v0.13+)
- **Node.js 20+** and **npm**
- **Docker** with **Docker Compose**
- *(Optional)* GNU Make (available by default on Linux/macOS)

---

## 2. Environment Configuration

Copy the example configuration files:

### Linux / macOS
```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

### Windows (PowerShell)
```powershell
Copy-Item .env.example .env
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
```

In `backend/.env`, ensure `DATABASE_URL` is configured:
```env
DATABASE_URL=postgresql+asyncpg://kontexa:kontexa_pass@localhost:5432/kontexa_db
```

---

## 3. Installing Dependencies

### Using Make
```bash
make setup
```

### Directly via CLI
```bash
# Backend
cd backend
uv sync

# Frontend
cd ../frontend
npm install
```

---

## 4. Running the Local Stack

### Option A: Complete Containerized Stack (Recommended)
Starts PostgreSQL 16 (with pgvector), Redis 7, Backend, and Frontend in Docker:

```bash
# Start services in background
make up
# (Or: docker compose -f infrastructure/docker/docker-compose.yml up -d)

# View running container status
docker compose -f infrastructure/docker/docker-compose.yml ps

# Stop services
make down
```

### Option B: Running Services Locally Outside Docker
Start PostgreSQL and Redis in Docker, then run Backend and Frontend locally with live code reload:

```bash
# 1. Start only database and cache
docker compose -f infrastructure/docker/docker-compose.yml up -d postgres redis

# 2. Apply database migrations
cd backend
uv run alembic upgrade head

# 3. Start Backend server
uv run uvicorn kontexa.main:app --reload --port 8000

# 4. In a separate terminal, start Frontend server
cd frontend
npm run dev
```

- Backend API: `http://localhost:8000` (Health: `http://localhost:8000/health`)
- Swagger Docs: `http://localhost:8000/docs`
- Frontend UI: `http://localhost:3000`
