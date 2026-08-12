"""Shared pytest configuration for backend tests."""

import os

# Settings is a module-level singleton. All env vars it requires must be present
# before any test module is imported, even when tests mock the actual connections.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test_db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

# Isolate test collection from any DEBUG value set in the developer's shell.
os.environ["DEBUG"] = "false"
