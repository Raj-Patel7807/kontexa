"""Unit test suite for health check API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient
from redis.exceptions import ConnectionError as RedisConnectionError

from kontexa.api import health as health_api
from kontexa.main import app


@pytest.mark.asyncio
async def test_health_check_returns_readiness_details_when_dependencies_are_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify GET /health reports live dependency checks when the service is ready."""

    async def available() -> None:
        """Represent a successful dependency probe."""

    monkeypatch.setattr(health_api, "check_database_connection", available)
    monkeypatch.setattr(health_api, "check_redis_connection", available)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "kontexa"
    assert data["version"] == "0.1.0"
    assert data["environment"] == "development"
    assert data["dependencies"] == {
        "database": {"status": "ok", "latency_ms": pytest.approx(0, abs=100)},
        "redis": {"status": "ok", "latency_ms": pytest.approx(0, abs=100)},
    }
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_health_check_returns_503_when_a_dependency_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify dependency failures are reflected without exposing connection details."""

    async def available() -> None:
        """Represent a successful dependency probe."""

    async def unavailable() -> None:
        """Represent an unavailable Redis dependency."""
        raise RedisConnectionError("connection refused")

    monkeypatch.setattr(health_api, "check_database_connection", available)
    monkeypatch.setattr(health_api, "check_redis_connection", unavailable)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert data["dependencies"]["database"]["status"] == "ok"
    assert data["dependencies"]["redis"]["status"] == "unavailable"
    assert "connection refused" not in response.text


@pytest.mark.asyncio
async def test_api_v1_health_check_returns_the_same_readiness_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify the versioned endpoint remains compatible with the root health endpoint."""

    async def available() -> None:
        """Represent a successful dependency probe."""

    monkeypatch.setattr(health_api, "check_database_connection", available)
    monkeypatch.setattr(health_api, "check_redis_connection", available)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
