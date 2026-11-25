"""Main FastAPI application entrypoint and app factory for Kontexa Backend API."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from kontexa.api.auth import router as auth_router
from kontexa.api.health import router as health_router
from kontexa.api.workspaces import router as workspaces_router
from kontexa.core.config import Settings
from kontexa.core.config import settings as default_settings
from kontexa.core.exceptions import register_exception_handlers
from kontexa.core.logging import RequestIdMiddleware, configure_logging
from kontexa.database.redis import close_redis_connection
from kontexa.database.session import close_database_engine

logger = logging.getLogger(__name__)

OPENAPI_TAGS = [
    {
        "name": "Health",
        "description": "Liveness, readiness, and dependency health verification endpoints.",
    },
    {
        "name": "Authentication",
        "description": "User account registration, session authentication, and logout endpoints.",
    },
    {
        "name": "Workspaces & Projects",
        "description": "Multi-tenant workspace isolation, RBAC membership, and project CRUD.",
    },
    {
        "name": "System",
        "description": "Operational diagnostics and system configuration metadata.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager handling startup validation and graceful resource release."""
    app_settings: Settings = getattr(app.state, "settings", default_settings)

    logger.info(
        "Initializing %s (v%s) in '%s' environment (debug=%s)...",
        app_settings.app_name,
        app_settings.app_version,
        app_settings.app_env,
        app_settings.debug,
    )
    yield

    logger.info("Executing graceful shutdown for %s...", app_settings.app_name)

    # Clean up Redis connection pool
    try:
        await close_redis_connection()
    except Exception as exc:
        logger.error("Error closing Redis connection during shutdown: %s", exc)

    # Clean up database engine pool
    try:
        await close_database_engine()
    except Exception as exc:
        logger.error("Error closing database engine during shutdown: %s", exc)

    logger.info("Shutdown complete for %s.", app_settings.app_name)


def create_app(settings_override: Settings | None = None) -> FastAPI:
    """FastAPI application factory supporting configurable settings injection."""
    app_settings = settings_override or default_settings

    # Initialize structured logging with configured log level
    configure_logging(app_settings.log_level)

    app = FastAPI(
        title=app_settings.app_name,
        description=(
            "Kontexa AI Software Engineering Workspace — Modular monolith API providing "
            "context-aware codebase intelligence, document retrieval, and gated development tasks."
        ),
        version=app_settings.app_version,
        openapi_tags=OPENAPI_TAGS,
        contact={
            "name": "Kontexa Engineering",
            "email": "rajpatel7807@gmail.com",
        },
        license_info={
            "name": "Apache 2.0",
            "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
        },
        lifespan=lifespan,
    )

    # Attach settings to application state for runtime inspection
    app.state.settings = app_settings

    # Register Request ID and transaction logging middleware
    app.add_middleware(RequestIdMiddleware)

    # Register Cross-Origin Resource Sharing (CORS) middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["x-request-id"],
    )

    # Register global domain exception handlers
    register_exception_handlers(app)

    # Register API routers
    app.include_router(health_router)
    app.include_router(auth_router, prefix=app_settings.api_v1_prefix)
    # Also mount auth router at /auth for convenient top-level routing
    app.include_router(auth_router)
    app.include_router(workspaces_router, prefix=app_settings.api_v1_prefix)
    app.include_router(workspaces_router)

    return app


# Default application instance for ASGI servers
app = create_app()

if __name__ == "__main__":
    import sys
    from pathlib import Path

    import uvicorn

    # Ensure src directory is in sys.path when script is executed directly
    src_dir = Path(__file__).resolve().parent.parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    uvicorn.run(
        "kontexa.main:app",
        host=default_settings.host,
        port=default_settings.port,
        reload=default_settings.debug,
    )
