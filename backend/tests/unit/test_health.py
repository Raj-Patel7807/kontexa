"""Unit test suite for health check API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from kontexa.main import app


@pytest.mark.asyncio
async def test_health_check_returns_200_and_valid_json() -> None:
    """Verify GET /health returns 200 OK with expected status and application metadata."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "kontexa"
    assert "environment" in data


@pytest.mark.asyncio
async def test_api_v1_health_check_returns_200_and_valid_json() -> None:
    """Verify GET /api/v1/health returns 200 OK with expected status and application metadata."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "kontexa"
    assert "environment" in data
