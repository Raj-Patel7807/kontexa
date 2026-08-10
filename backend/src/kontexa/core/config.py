"""Application configuration management using Pydantic Settings."""

import ssl
from pathlib import Path
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings class loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="Kontexa Backend", description="Application name")
    app_env: str = Field(default="development", description="Current execution environment")
    debug: bool = Field(default=False, description="Debug mode toggle")
    log_level: str = Field(default="INFO", description="Logging output level")

    host: str = Field(default="0.0.0.0", description="API server host bind address")
    port: int = Field(default=8000, description="API server port bind address")

    database_url: str = Field(
        default="postgresql+asyncpg://kontexa:kontexa_pass@localhost:5432/kontexa_db",
        description="Async SQLAlchemy database connection string",
    )
    database_pool_size: int = Field(
        default=5,
        description="SQLAlchemy connection pool size (keep low for Aiven free tier)",
    )
    database_max_overflow: int = Field(
        default=10,
        description="Maximum overflow connections beyond pool_size",
    )
    database_ca_cert: str | None = Field(
        default=None,
        description="Absolute path to the CA certificate for SSL database connections (Aiven)",
    )
    database_ssl_mode: Literal["disable", "require"] = Field(
        default="disable",
        description="TLS mode for database connections; use require for Aiven",
    )

    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis server connection string",
    )

    cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origin domains",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_sync_url(self) -> str:
        """Derive a synchronous database URL for Alembic migrations.

        Alembic runs migrations synchronously and cannot use asyncpg.
        This replaces the async driver with psycopg2.
        """
        return self.database_url.replace("+asyncpg", "+psycopg2")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_ssl_context(self) -> ssl.SSLContext | None:
        """Build an SSL context when a CA certificate is configured.

        Aiven PostgreSQL requires TLS connections. The CA certificate
        is downloaded from the Aiven console and its path is set via
        the DATABASE_CA_CERT environment variable.
        """
        if not self.database_ca_cert:
            return None

        ca_path = Path(self.database_ca_cert)
        if not ca_path.exists():
            return None

        ctx = ssl.create_default_context(cafile=str(ca_path))
        return ctx

    @property
    def database_connect_args(self) -> dict[str, ssl.SSLContext | bool]:
        """Build asyncpg connection arguments for the configured TLS mode."""
        if self.database_ssl_mode == "disable":
            return {}

        ssl_context = self.database_ssl_context
        if ssl_context is not None:
            return {"ssl": ssl_context}
        return {"ssl": True}


settings = Settings()
