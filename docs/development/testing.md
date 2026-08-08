# Testing & Verification Guide

This document outlines the testing, linting, and type checking workflows for Kontexa.

---

## 1. Quick Verification Commands

Execute all repository verification checks using Make:

```bash
# Run backend tests and frontend type checks
make test

# Run backend and frontend linter checks
make lint

# Format Python codebase
make format
```

---

## 2. Backend Testing & Verification

### Running Pytest Suite

```bash
cd backend
uv run pytest
```

### Running Linter & Formatter

```bash
cd backend
# Check for lint issues
uv run ruff check .

# Check formatting compliance
uv run ruff format --check .

# Automatically apply formatting
uv run ruff format .
```

---

## 3. Frontend Verification

### Running Linter & Type Check

```bash
cd frontend
# Run ESLint
npm run lint

# Run TypeScript type check
npm run typecheck

# Test production build
npm run build
```

---

## 4. Continuous Integration Expectations

Pull requests must pass all CI workflow checks:
- Backend Ruff linting & formatting compliance
- Backend Pytest execution
- Frontend ESLint verification
- Frontend TypeScript type checking
- Frontend Next.js production build verification
