"""Application configuration management using Pydantic Settings.

Enforces typed configuration loading from environment variables,
with strict fail-fast validation for production environments.
"""

import ssl
from pathlib import Path
from typing import Literal

from pydantic import Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings class loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application metadata
    app_name: str = Field(default="Kontexa Backend", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    app_env: Literal["development", "staging", "production", "test"] = Field(
        default="development", description="Current execution environment"
    )
    api_v1_prefix: str = Field(default="/api/v1", description="Prefix for version 1 API endpoints")
    debug: bool = Field(default=False, description="Debug mode toggle")
    log_level: str = Field(default="INFO", description="Logging output level")

    # Network bind settings
    host: str = Field(default="0.0.0.0", description="API server host bind address")
    port: int = Field(default=8000, description="API server port bind address")

    # PostgreSQL database settings
    database_url: str = Field(
        description="Async SQLAlchemy database connection string",
    )
    database_pool_size: int = Field(
        default=5,
        description="SQLAlchemy connection pool size (keep low for cloud free tier)",
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
        description="TLS mode for database connections; use require for Aiven/cloud",
    )

    # Redis cache and queue settings
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis server connection string",
    )
    health_check_timeout_seconds: float = Field(
        default=2.0,
        gt=0,
        description="Maximum time allowed for each dependency health check",
    )

    # Cross-Origin Resource Sharing (CORS)
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origin domains",
    )

    @model_validator(mode="after")
    def validate_production_invariants(self) -> "Settings":
        """Fail fast if insecure settings are configured in production environment."""
        if self.app_env == "production":
            if self.debug:
                raise ValueError("DEBUG must be False in production environment.")

            if self.database_ssl_mode != "require":
                raise ValueError("DATABASE_SSL_MODE must be 'require' in production environment.")

            for origin in self.cors_origins:
                if origin == "*":
                    raise ValueError(
                        "CORS wildcard '*' is strictly prohibited in production environment."
                    )
                if "localhost" in origin or "127.0.0.1" in origin:
                    raise ValueError(
                        f"Insecure local CORS origin '{origin}' is not permitted in production."
                    )

            if "localhost" in self.database_url or "127.0.0.1" in self.database_url:
                raise ValueError(
                    "DATABASE_URL must point to a remote managed database in production."
                )

        return self

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

        Managed PostgreSQL (such as Aiven) requires TLS connections.
        The CA certificate path is set via the DATABASE_CA_CERT variable.
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


# Global settings singleton loaded from environment
settings = Settings()  # type: ignore[call-arg]
