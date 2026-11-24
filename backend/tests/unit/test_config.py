"""Unit tests for application configuration and Aiven database settings."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from kontexa.core.config import Settings


def test_default_settings_load_without_error() -> None:
    """Verify Settings instantiates with default values when no env vars are set."""
    s = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://test:test@localhost:5432/test_db",
    )
    assert s.app_name == "Kontexa Backend"
    assert s.app_version == "0.1.0"
    assert s.app_env == "development"
    assert s.database_pool_size == 5
    assert s.database_max_overflow == 10
    assert s.health_check_timeout_seconds == 2.0


def test_database_sync_url_replaces_asyncpg_with_psycopg2() -> None:
    """Verify the sync URL derivation swaps the async driver for Alembic compatibility."""
    s = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://user:pass@host:5432/db",
    )
    assert s.database_sync_url == "postgresql+psycopg2://user:pass@host:5432/db"


def test_database_sync_url_preserves_query_params() -> None:
    """Verify sync URL derivation keeps query parameters like sslmode intact."""
    s = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://user:pass@host:5432/db?sslmode=require",
    )
    assert s.database_sync_url == "postgresql+psycopg2://user:pass@host:5432/db?sslmode=require"


def test_database_ssl_context_is_none_when_no_cert_configured() -> None:
    """Verify no SSL context is created when DATABASE_CA_CERT is not set."""
    s = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://test:test@localhost:5432/test_db",
        database_ca_cert=None,
    )
    assert s.database_ssl_context is None


def test_database_ssl_context_is_none_when_cert_path_does_not_exist() -> None:
    """Verify no SSL context is created when the cert file is missing."""
    s = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://test:test@localhost:5432/test_db",
        database_ca_cert="/nonexistent/path/ca.pem",
    )
    assert s.database_ssl_context is None


def test_database_ssl_context_is_created_when_valid_cert_exists() -> None:
    """Verify a configured certificate path is passed to SSL context construction."""
    with tempfile.NamedTemporaryFile(suffix=".pem", delete=False, mode="w") as file:
        cert_path = file.name

    context = Mock()
    try:
        with patch(
            "kontexa.core.config.ssl.create_default_context", return_value=context
        ) as create:
            settings = Settings(
                _env_file=None,
                database_url="postgresql+asyncpg://test:test@localhost:5432/test_db",
                database_ca_cert=cert_path,
                database_ssl_mode="require",
            )
            assert settings.database_connect_args == {"ssl": context}
            create.assert_called_once_with(cafile=cert_path)
    finally:
        Path(cert_path).unlink(missing_ok=True)


def test_database_connect_args_enable_tls_without_a_ca_certificate() -> None:
    """Verify Aiven connections remain encrypted when a CA path is supplied separately."""
    settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://test:test@localhost:5432/test_db",
        database_ssl_mode="require",
    )
    assert settings.database_connect_args == {"ssl": True}


def test_database_connect_args_disable_tls_for_local_development() -> None:
    """Verify local Docker PostgreSQL does not receive unsupported TLS arguments."""
    settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://test:test@localhost:5432/test_db",
        database_ssl_mode="disable",
    )
    assert settings.database_connect_args == {}


def test_database_pool_size_is_configurable() -> None:
    """Verify pool settings can be overridden."""
    s = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://test:test@localhost:5432/test_db",
        database_pool_size=3,
        database_max_overflow=5,
    )
    assert s.database_pool_size == 3
    assert s.database_max_overflow == 5


def test_cors_origins_default() -> None:
    """Verify CORS origins defaults to localhost:3000."""
    s = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://test:test@localhost:5432/test_db",
    )
    assert s.cors_origins == ["http://localhost:3000"]
    assert s.api_v1_prefix == "/api/v1"


def test_production_fails_when_debug_is_enabled() -> None:
    """Verify production environment rejects debug=True."""
    import pytest

    with pytest.raises(ValueError, match="DEBUG must be False in production environment"):
        Settings(
            _env_file=None,
            app_env="production",
            debug=True,
            database_ssl_mode="require",
            database_url="postgresql+asyncpg://user:pass@db.example.com:5432/db",
            cors_origins=["https://app.kontexa.ai"],
        )


def test_production_fails_when_ssl_mode_is_disabled() -> None:
    """Verify production environment rejects disabled database SSL mode."""
    import pytest

    with pytest.raises(
        ValueError, match="DATABASE_SSL_MODE must be 'require' in production environment"
    ):
        Settings(
            _env_file=None,
            app_env="production",
            debug=False,
            database_ssl_mode="disable",
            database_url="postgresql+asyncpg://user:pass@db.example.com:5432/db",
            cors_origins=["https://app.kontexa.ai"],
        )


def test_production_fails_when_cors_contains_wildcard() -> None:
    """Verify production environment rejects wildcard CORS origins."""
    import pytest

    with pytest.raises(ValueError, match=r"CORS wildcard '\*' is strictly prohibited"):
        Settings(
            _env_file=None,
            app_env="production",
            debug=False,
            database_ssl_mode="require",
            database_url="postgresql+asyncpg://user:pass@db.example.com:5432/db",
            cors_origins=["*"],
        )


def test_production_fails_when_cors_contains_localhost() -> None:
    """Verify production environment rejects localhost in CORS origins."""
    import pytest

    with pytest.raises(ValueError, match="is not permitted in production"):
        Settings(
            _env_file=None,
            app_env="production",
            debug=False,
            database_ssl_mode="require",
            database_url="postgresql+asyncpg://user:pass@db.example.com:5432/db",
            cors_origins=["https://app.kontexa.ai", "http://localhost:3000"],
        )


def test_production_fails_when_database_points_to_localhost() -> None:
    """Verify production environment rejects localhost database hostnames."""
    import pytest

    with pytest.raises(ValueError, match="DATABASE_URL must point to a remote managed database"):
        Settings(
            _env_file=None,
            app_env="production",
            debug=False,
            database_ssl_mode="require",
            database_url="postgresql+asyncpg://user:pass@127.0.0.1:5432/db",
            cors_origins=["https://app.kontexa.ai"],
        )


def test_valid_production_settings_pass() -> None:
    """Verify valid production settings instantiate without error."""
    s = Settings(
        _env_file=None,
        app_env="production",
        debug=False,
        database_ssl_mode="require",
        database_url="postgresql+asyncpg://user:pass@db.example.com:5432/db",
        cors_origins=["https://app.kontexa.ai"],
    )
    assert s.app_env == "production"
    assert s.debug is False
    assert s.database_ssl_mode == "require"
