"""Application configuration management using Pydantic Settings."""

from pydantic import Field
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
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis server connection string",
    )

    cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origin domains",
    )


settings = Settings()
