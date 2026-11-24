"""Structured logging configuration and Request ID context tracking for Kontexa."""

import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable holding the active request correlation ID across async tasks
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Logging filter that injects the current request correlation ID into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


def configure_logging(log_level: str = "INFO") -> None:
    """Configure application-wide logging with request ID injection and standard format."""
    handler = logging.StreamHandler()
    handler.addFilter(RequestIdFilter())
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s"
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    # Replace existing handlers with our configured handler
    root_logger.handlers = [handler]


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware that assigns or propagates request correlation IDs and logs HTTP transactions."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Extract existing X-Request-ID or generate a new UUID4 identifier
        header_request_id = request.headers.get("x-request-id")
        request_id = header_request_id.strip() if header_request_id else str(uuid.uuid4())

        # Store in context variable for logging filter
        token = request_id_ctx.set(request_id)
        # Also store on request state so outer exception handlers can access it
        request.state.request_id = request_id
        start_time = time.perf_counter()

        logger = logging.getLogger("kontexa.api.access")
        logger.info("--> %s %s", request.method, request.url.path)

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            # Attach correlation ID to outbound response headers
            response.headers["x-request-id"] = request_id
            logger.info(
                "<-- %s %s status=%d duration=%.2fms",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )
            return response

        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error(
                "<-- %s %s EXCEPTION=%s duration=%.2fms",
                request.method,
                request.url.path,
                type(exc).__name__,
                duration_ms,
            )
            raise

        finally:
            request_id_ctx.reset(token)
