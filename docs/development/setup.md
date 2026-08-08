# Local Development Setup Guide

This guide walks through setting up the Kontexa repository for local development.

---

## Prerequisites

Ensure the following tools are installed on your machine:

- **Python**: 3.12 or newer
- **uv**: Python package and environment manager (`uv --version`)
- **Node.js**: LTS version (`v20+` or `v24+`)
- **Docker & Docker Compose**: For local PostgreSQL and Redis services
- **Make**: Build and development task automation

---

## Step-by-Step Setup

### 1. Environment Files

Copy the example environment configuration files:

```bash
# Root environment file
cp .env.example .env

# Backend environment file
cp backend/.env.example backend/.env

# Frontend environment file
cp frontend/.env.example frontend/.env
```

### 2. Dependency Installation

Install dependencies for both Python (via `uv`) and Node.js (via `npm`):

```bash
make setup
```

Alternatively, install individually:

```bash
# Backend dependencies
cd backend && uv sync

# Frontend dependencies
cd frontend && npm install
```

### 3. Start Local Infrastructure

Boot the local PostgreSQL (with `pgvector`) and Redis containers:

```bash
make up
```

Verify containers are running:

```bash
docker compose -f infrastructure/docker/docker-compose.yml ps
```

### 4. Running Development Servers

Start both frontend and backend development servers using Make:

```bash
make dev
```

Or start them manually in separate terminals:

- **Backend** (FastAPI at `http://localhost:8000`):
  ```bash
  cd backend && uv run uvicorn kontexa.main:app --reload --port 8000
  ```
- **Frontend** (Next.js at `http://localhost:3000`):
  ```bash
  cd frontend && npm run dev
  ```
