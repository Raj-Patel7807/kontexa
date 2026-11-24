"""Domain exception hierarchy and global FastAPI exception handlers for Kontexa."""

import logging
from typing import Any

from fastapi import FastAPI, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request

from kontexa.core.logging import request_id_ctx

logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    """Standardized API error response payload returned to clients."""

    detail: str = Field(description="Human-readable error description")
    code: str = Field(description="Machine-readable error classification code")
    request_id: str = Field(description="Request correlation identifier for diagnostics")
    errors: list[Any] | None = Field(
        default=None, description="Granular field validation error details"
    )


class KontexaError(Exception):
    """Base exception for all internal Kontexa domain and business logic errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class ResourceNotFoundError(KontexaError):
    """Raised when an entity or resource does not exist or is inaccessible."""

    def __init__(self, message: str = "Resource not found", code: str = "NOT_FOUND") -> None:
        super().__init__(message, code=code, status_code=status.HTTP_404_NOT_FOUND)


class PermissionDeniedError(KontexaError):
    """Raised when an authenticated actor lacks required permissions for a workspace resource."""

    def __init__(self, message: str = "Permission denied", code: str = "PERMISSION_DENIED") -> None:
        super().__init__(message, code=code, status_code=status.HTTP_403_FORBIDDEN)


class AuthenticationError(KontexaError):
    """Raised when authentication credentials or session tokens are invalid or missing."""

    def __init__(
        self, message: str = "Authentication required", code: str = "UNAUTHORIZED"
    ) -> None:
        super().__init__(message, code=code, status_code=status.HTTP_401_UNAUTHORIZED)


class ValidationError(KontexaError):
    """Raised when incoming business parameters fail domain validation checks."""

    def __init__(self, message: str = "Validation failed", code: str = "VALIDATION_ERROR") -> None:
        super().__init__(message, code=code, status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)


class ConflictError(KontexaError):
    """Raised when a resource mutation encounters a state conflict (e.g. duplicate slug)."""

    def __init__(self, message: str = "Resource conflict", code: str = "CONFLICT") -> None:
        super().__init__(message, code=code, status_code=status.HTTP_409_CONFLICT)


# Aliases for backwards compatibility
KontexaException = KontexaError
ResourceNotFoundException = ResourceNotFoundError
PermissionDeniedException = PermissionDeniedError
AuthenticationException = AuthenticationError
ValidationException = ValidationError
ConflictException = ConflictError


def _extract_request_id(request: Request) -> str:
    """Extract correlation request ID from request state, context var, or incoming headers."""
    state_id: str | None = getattr(request.state, "request_id", None)
    if state_id:
        return state_id
    ctx_id = request_id_ctx.get()
    if ctx_id and ctx_id != "-":
        return ctx_id
    header_id = request.headers.get("x-request-id")
    if header_id:
        return header_id.strip()
    return "-"


async def kontexa_exception_handler(request: Request, exc: KontexaError) -> JSONResponse:
    """Format domain exceptions into standardized JSON error responses."""
    request_id = _extract_request_id(request)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            detail=exc.message,
            code=exc.code,
            request_id=request_id,
        ).model_dump(exclude_none=True),
        headers={"x-request-id": request_id},
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Format Starlette and FastAPI HTTPExceptions into standardized JSON error responses."""
    request_id = _extract_request_id(request)
    detail = exc.detail if isinstance(exc.detail, str) else "HTTP error"
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            detail=detail,
            code="HTTP_ERROR",
            request_id=request_id,
        ).model_dump(exclude_none=True),
        headers={"x-request-id": request_id},
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Format Pydantic schema validation errors into structured JSON responses."""
    request_id = _extract_request_id(request)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=ErrorResponse(
            detail="Request validation failed",
            code="VALIDATION_ERROR",
            request_id=request_id,
            errors=list(exc.errors()),
        ).model_dump(exclude_none=True),
        headers={"x-request-id": request_id},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler masking internal server errors and preserving correlation IDs."""
    request_id = _extract_request_id(request)
    logger.exception(
        "Unhandled server exception processing %s %s [request_id=%s]",
        request.method,
        request.url.path,
        request_id,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            detail="An internal server error occurred.",
            code="INTERNAL_SERVER_ERROR",
            request_id=request_id,
        ).model_dump(exclude_none=True),
        headers={"x-request-id": request_id},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the FastAPI application instance."""
    app.add_exception_handler(KontexaError, kontexa_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)
