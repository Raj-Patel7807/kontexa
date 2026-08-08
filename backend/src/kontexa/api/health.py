"""Health check API endpoints for application status verification."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from kontexa.core.config import settings

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Schema representing health check verification status."""

    status: str = Field(
        description="Status of the application service", json_schema_extra={"example": "ok"}
    )
    app: str = Field(
        description="Name of the application", json_schema_extra={"example": "kontexa"}
    )
    environment: str = Field(
        description="Execution environment", json_schema_extra={"example": "development"}
    )


@router.get("/health", response_model=HealthResponse, summary="Application Health Check")
@router.get("/api/v1/health", response_model=HealthResponse, summary="API v1 Health Check")
async def health_check() -> HealthResponse:
    """Return health status of the backend API service."""
    return HealthResponse(
        status="ok",
        app="kontexa",
        environment=settings.app_env,
    )
