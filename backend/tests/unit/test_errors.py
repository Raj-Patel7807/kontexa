"""Unit tests for middleware, request correlation IDs, app factory, and exception handlers."""

import pytest
from fastapi import APIRouter, HTTPException, status
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from kontexa.core.config import Settings
from kontexa.core.exceptions import (
    AuthenticationError,
    ConflictError,
    PermissionDeniedError,
    ResourceNotFoundError,
    ValidationError,
)
from kontexa.main import create_app

# Router with dummy endpoints to trigger various error conditions
dummy_errors_router = APIRouter(prefix="/test-errors")


class ItemPayload(BaseModel):
    name: str
    count: int


@dummy_errors_router.get("/not-found")
async def trigger_not_found() -> None:
    raise ResourceNotFoundError("Workspace item not found")


@dummy_errors_router.get("/permission-denied")
async def trigger_permission_denied() -> None:
    raise PermissionDeniedError("Admin role required")


@dummy_errors_router.get("/unauthorized")
async def trigger_unauthorized() -> None:
    raise AuthenticationError("Session expired")


@dummy_errors_router.get("/validation-error")
async def trigger_domain_validation() -> None:
    raise ValidationError("Invalid plan configuration")


@dummy_errors_router.get("/conflict")
async def trigger_conflict() -> None:
    raise ConflictError("Resource slug already in use")


@dummy_errors_router.get("/http-exception")
async def trigger_http_exception() -> None:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bad request syntax")


@dummy_errors_router.get("/unhandled")
async def trigger_unhandled() -> None:
    raise RuntimeError("Unexpected internal crash with sensitive database credentials")


@dummy_errors_router.post("/validate-body")
async def validate_body(payload: ItemPayload) -> dict[str, str]:
    return {"status": "ok", "name": payload.name}


@pytest.fixture
def error_app():
    """Create a FastAPI application with registered error test endpoints."""
    settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://test:test@localhost:5432/test_db",
        debug=False,
    )
    app = create_app(settings_override=settings)
    app.include_router(dummy_errors_router)
    return app


@pytest.mark.asyncio
async def test_request_id_generated_when_absent(error_app) -> None:
    """Verify X-Request-ID is automatically generated and returned in headers."""
    async with AsyncClient(
        transport=ASGITransport(app=error_app), base_url="http://test"
    ) as client:
        response = await client.get("/live")

    assert response.status_code == 200
    assert "x-request-id" in response.headers
    assert len(response.headers["x-request-id"]) > 0


@pytest.mark.asyncio
async def test_request_id_propagated_when_supplied(error_app) -> None:
    """Verify incoming X-Request-ID header is preserved and echoed back."""
    custom_id = "custom-trace-id-12345"
    async with AsyncClient(
        transport=ASGITransport(app=error_app), base_url="http://test"
    ) as client:
        response = await client.get("/live", headers={"x-request-id": custom_id})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == custom_id


@pytest.mark.asyncio
async def test_resource_not_found_exception_handling(error_app) -> None:
    """Verify ResourceNotFoundError returns 404 with structured JSON payload."""
    async with AsyncClient(
        transport=ASGITransport(app=error_app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/test-errors/not-found", headers={"x-request-id": "req-not-found"}
        )

    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Workspace item not found"
    assert data["code"] == "NOT_FOUND"
    assert data["request_id"] == "req-not-found"


@pytest.mark.asyncio
async def test_permission_denied_exception_handling(error_app) -> None:
    """Verify PermissionDeniedError returns 403 with structured JSON payload."""
    async with AsyncClient(
        transport=ASGITransport(app=error_app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/test-errors/permission-denied", headers={"x-request-id": "req-perm-denied"}
        )

    assert response.status_code == 403
    data = response.json()
    assert data["detail"] == "Admin role required"
    assert data["code"] == "PERMISSION_DENIED"
    assert data["request_id"] == "req-perm-denied"


@pytest.mark.asyncio
async def test_authentication_exception_handling(error_app) -> None:
    """Verify AuthenticationError returns 401 with structured JSON payload."""
    async with AsyncClient(
        transport=ASGITransport(app=error_app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/test-errors/unauthorized", headers={"x-request-id": "req-unauth"}
        )

    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Session expired"
    assert data["code"] == "UNAUTHORIZED"
    assert data["request_id"] == "req-unauth"


@pytest.mark.asyncio
async def test_domain_validation_exception_handling(error_app) -> None:
    """Verify ValidationError returns 422 with structured JSON payload."""
    async with AsyncClient(
        transport=ASGITransport(app=error_app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/test-errors/validation-error", headers={"x-request-id": "req-val-error"}
        )

    assert response.status_code == 422
    data = response.json()
    assert data["detail"] == "Invalid plan configuration"
    assert data["code"] == "VALIDATION_ERROR"
    assert data["request_id"] == "req-val-error"


@pytest.mark.asyncio
async def test_conflict_exception_handling(error_app) -> None:
    """Verify ConflictError returns 409 with structured JSON payload."""
    async with AsyncClient(
        transport=ASGITransport(app=error_app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/test-errors/conflict", headers={"x-request-id": "req-conflict"}
        )

    assert response.status_code == 409
    data = response.json()
    assert data["detail"] == "Resource slug already in use"
    assert data["code"] == "CONFLICT"
    assert data["request_id"] == "req-conflict"


@pytest.mark.asyncio
async def test_starlette_http_exception_handling(error_app) -> None:
    """Verify Starlette HTTPException returns structured JSON payload."""
    async with AsyncClient(
        transport=ASGITransport(app=error_app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/test-errors/http-exception", headers={"x-request-id": "req-http-err"}
        )

    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Bad request syntax"
    assert data["code"] == "HTTP_ERROR"
    assert data["request_id"] == "req-http-err"


@pytest.mark.asyncio
async def test_schema_validation_error_returns_422_with_details(error_app) -> None:
    """Verify RequestValidationError captures invalid field details in error response."""
    async with AsyncClient(
        transport=ASGITransport(app=error_app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/test-errors/validate-body",
            json={"name": 1234, "count": "not-an-int"},
            headers={"x-request-id": "req-schema-val"},
        )

    assert response.status_code == 422
    data = response.json()
    assert data["detail"] == "Request validation failed"
    assert data["code"] == "VALIDATION_ERROR"
    assert data["request_id"] == "req-schema-val"
    assert "errors" in data
    assert len(data["errors"]) > 0


@pytest.mark.asyncio
async def test_unhandled_exception_masks_internal_details(error_app) -> None:
    """Verify unhandled exceptions return 500 without leaking stack traces or sensitive info."""
    async with AsyncClient(
        transport=ASGITransport(app=error_app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        response = await client.get("/test-errors/unhandled", headers={"x-request-id": "req-crash"})

    assert response.status_code == 500
    data = response.json()
    assert data["detail"] == "An internal server error occurred."
    assert data["code"] == "INTERNAL_SERVER_ERROR"
    assert data["request_id"] == "req-crash"
    assert "credentials" not in response.text
