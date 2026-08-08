.PHONY: help setup dev up down test lint format build clean

help: ## Display available Makefile commands and descriptions
	@echo "Kontexa Development Commands:"
	@echo "  make setup   - Install backend (uv) and frontend (npm) dependencies"
	@echo "  make dev     - Run backend and frontend local development servers"
	@echo "  make up      - Start Docker Compose services (PostgreSQL, Redis, Apps)"
	@echo "  make down    - Stop Docker Compose services"
	@echo "  make test    - Run backend pytest suite and frontend typecheck"
	@echo "  make lint    - Run ruff linter on backend and ESLint on frontend"
	@echo "  make format  - Format backend Python code with ruff"
	@echo "  make build   - Build frontend Next.js production bundle"
	@echo "  make clean   - Remove Python __pycache__, build output, and caches"

setup: ## Install backend and frontend dependencies
	cd backend && uv sync
	cd frontend && npm install

dev: ## Run development environment locally
	cd backend && uv run uvicorn kontexa.main:app --reload --port 8000 & \
	cd frontend && npm run dev

up: ## Start Docker Compose services
	docker compose -f infrastructure/docker/docker-compose.yml up -d

down: ## Stop Docker Compose services
	docker compose -f infrastructure/docker/docker-compose.yml down

test: ## Run backend pytest test suite and frontend typecheck
	cd backend && uv run pytest
	cd frontend && npm run typecheck

lint: ## Run code linter checks
	cd backend && uv run ruff check .
	cd frontend && npm run lint

format: ## Format codebases
	cd backend && uv run ruff format .

build: ## Build frontend production application
	cd frontend && npm run build

clean: ## Remove caches and build artifacts
	@echo "Cleaning cache and build directories..."
	@for /d /r . %%d in (__pycache__ .pytest_cache .ruff_cache .next node_modules_cache) do @if exist "%%d" rd /s /q "%%d" 2>nul || true
