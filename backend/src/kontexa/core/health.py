"""Dependency health-check orchestration for operational endpoints."""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal

from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from kontexa.core.config import settings

logger = logging.getLogger(__name__)

ComponentStatus = Literal["ok", "unavailable"]
HealthCheckOperation = Callable[[], Awaitable[None]]


@dataclass(frozen=True)
class ComponentHealth:
    """Result of checking one external application dependency."""

    status: ComponentStatus
    latency_ms: float


async def check_component(name: str, operation: HealthCheckOperation) -> ComponentHealth:
    """Run a dependency check with a timeout and record its observed latency."""
    started_at = time.perf_counter()

    try:
        await asyncio.wait_for(operation(), timeout=settings.health_check_timeout_seconds)
    except (TimeoutError, OSError, RedisError, SQLAlchemyError) as error:
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.warning(
            "Dependency health check failed",
            extra={"component": name, "error_type": type(error).__name__},
        )
        return ComponentHealth(status="unavailable", latency_ms=latency_ms)

    latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
    return ComponentHealth(status="ok", latency_ms=latency_ms)
