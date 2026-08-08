"""Main FastAPI application entrypoint for Kontexa Backend API."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from kontexa.api.health import router as health_router
from kontexa.core.config import settings

# Configure basic logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager handling startup and shutdown events."""
    logger.info("Initializing %s in %s mode...", settings.app_name, settings.app_env)
    yield
    logger.info("Shutting down %s...", settings.app_name)


def create_app() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title=settings.app_name,
        description="Kontexa AI Workspace Backend Infrastructure API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(health_router)

    return app


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
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
