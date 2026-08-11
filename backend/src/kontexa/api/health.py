"""Health check API endpoints for application status verification."""

import asyncio
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field

from kontexa.core.config import settings
from kontexa.core.health import ComponentHealth, check_component
from kontexa.database.redis import check_redis_connection
from kontexa.database.session import check_database_connection

router = APIRouter(tags=["Health"])


class DependencyHealthResponse(BaseModel):
    """Schema representing the availability and latency of one dependency."""

    status: Literal["ok", "unavailable"]
    latency_ms: float = Field(ge=0)


class HealthResponse(BaseModel):
    """Schema representing the backend's readiness and dependency state."""

    status: Literal["ok", "degraded"] = Field(
        description="Overall backend readiness status", json_schema_extra={"example": "ok"}
    )
    service: str = Field(
        description="Stable service identifier", json_schema_extra={"example": "kontexa"}
    )
    environment: str = Field(
        description="Execution environment", json_schema_extra={"example": "development"}
    )
    version: str = Field(
        description="Backend application version", json_schema_extra={"example": "0.1.0"}
    )
    timestamp: datetime = Field(description="UTC timestamp for this readiness evaluation")
    dependencies: dict[str, DependencyHealthResponse] = Field(
        description="Availability and latency for required backend dependencies"
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={
        503: {"model": HealthResponse, "description": "A required dependency is unavailable"}
    },
    summary="Application readiness check",
)
@router.get(
    "/api/v1/health",
    response_model=HealthResponse,
    responses={
        503: {"model": HealthResponse, "description": "A required dependency is unavailable"}
    },
    summary="API v1 readiness check",
)
async def health_check(response: Response) -> HealthResponse:
    """Report backend readiness with live PostgreSQL and Redis dependency checks."""
    database, redis = await asyncio.gather(
        check_component("database", check_database_connection),
        check_component("redis", check_redis_connection),
    )
    dependencies = {"database": database, "redis": redis}
    is_ready = all(component.status == "ok" for component in dependencies.values())

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status="ok" if is_ready else "degraded",
        service="kontexa",
        environment=settings.app_env,
        version=settings.app_version,
        timestamp=datetime.now(UTC),
        dependencies={name: _to_response(component) for name, component in dependencies.items()},
    )


def _to_response(component: ComponentHealth) -> DependencyHealthResponse:
    """Translate an internal component check result into the public response schema."""
    return DependencyHealthResponse(status=component.status, latency_ms=component.latency_ms)
