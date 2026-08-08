"""Integration test for database session factory initialization."""

import pytest

from kontexa.database.session import AsyncSessionLocal, engine


@pytest.mark.asyncio
async def test_database_engine_and_session_initialization() -> None:
    """Verify SQLAlchemy engine and session factory are instantiated properly."""
    assert engine is not None
    async with AsyncSessionLocal() as session:
        assert session is not None
