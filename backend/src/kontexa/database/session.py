"""SQLAlchemy engine and session lifecycle management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from kontexa.core.config import settings


def _build_connect_args() -> dict:
    """Build SSL connection arguments for asyncpg when a CA certificate is configured."""
    connect_args: dict = {}
    ssl_ctx = settings.database_ssl_context
    if ssl_ctx is not None:
        connect_args["ssl"] = ssl_ctx
    return connect_args


# Asynchronous database engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    connect_args=_build_connect_args(),
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
