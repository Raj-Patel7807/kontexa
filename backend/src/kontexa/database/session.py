"""SQLAlchemy engine and session lifecycle management."""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from kontexa.core.config import settings

# Asynchronous database engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    connect_args=settings.database_connect_args,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base declarative class for future SQLAlchemy database models."""

    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency provider yielding an asynchronous SQLAlchemy database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_database_connection() -> None:
    """Verify PostgreSQL accepts a lightweight query through the application engine."""
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


async def close_database_engine() -> None:
    """Release pooled PostgreSQL connections during application shutdown."""
    await engine.dispose()
