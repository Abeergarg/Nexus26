"""
Centralized exception handling for Project Nexus26.

Provides:
  - NexusException base class and domain-specific subclasses.
  - GlobalExceptionMiddleware: catches all unhandled errors and returns clean JSON.
  - validation_exception_handler: maps Pydantic validation failures to structured JSON.
"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Any, Dict, List
import traceback

from app.core.logging import get_structured_logger

logger = get_structured_logger("ExceptionGateway")


# ---------------------------------------------------------------------------
# Domain Exception Hierarchy
# ---------------------------------------------------------------------------


class NexusException(Exception):
    """Base exception class for Project Nexus26."""

    def __init__(self, message: str, code: str = "NEXUS_ERROR", status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class RouteCalculationError(NexusException):
    """Triggered when Dijkstra routing fails or constraints are unsatisfiable."""

    def __init__(self, message: str):
        super().__init__(message, code="ROUTE_CALCULATION_FAILED", status_code=400)


class WeatherAPIError(NexusException):
    """Triggered when the external weather API fails after all retries."""

    def __init__(self, message: str):
        super().__init__(message, code="WEATHER_FETCH_FAILED", status_code=502)


class TelemetryIngestionError(NexusException):
    """Triggered when a telemetry event payload fails ingestion."""

    def __init__(self, message: str):
        super().__init__(message, code="TELEMETRY_INGESTION_FAILED", status_code=422)


class TopologyLoadError(NexusException):
    """Triggered when the stadium topology graph cannot be loaded from disk."""

    def __init__(self, message: str):
        super().__init__(message, code="TOPOLOGY_LOAD_FAILED", status_code=500)


class ResourceDepletionError(NexusException):
    """Triggered when a resource stock falls below a critical safety threshold."""

    def __init__(self, message: str):
        super().__init__(message, code="RESOURCE_CRITICAL", status_code=503)


# ---------------------------------------------------------------------------
# Global Exception Middleware
# ---------------------------------------------------------------------------


class GlobalExceptionMiddleware(BaseHTTPMiddleware):
    """
    Middleware that intercepts all unhandled errors, logs a structured traceback,
    and returns a clean JSON error response to prevent stack trace leaks.

    Request ID is injected into every error response for traceability.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        from app.core.context import get_current_request_id

        request_id = get_current_request_id()

        try:
            return await call_next(request)
        except Exception as exc:
            if isinstance(exc, NexusException):
                logger.warning(
                    f"Nexus domain error: {exc.message}",
                    extra={
                        "error_code": exc.code,
                        "status_code": exc.status_code,
                        "path": request.url.path,
                        "method": request.method,
                        "request_id": request_id,
                    },
                )
                return JSONResponse(
                    status_code=exc.status_code,
                    content={
                        "success": False,
                        "request_id": request_id,
                        "error": {"code": exc.code, "message": exc.message},
                    },
                )

            # Unexpected system-level crashes
            tb = traceback.format_exc()
            logger.error(
                f"Unhandled exception: {str(exc)}",
                extra={
                    "traceback": tb,
                    "path": request.url.path,
                    "method": request.method,
                    "request_id": request_id,
                },
            )
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "request_id": request_id,
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected error occurred. Please consult venue administrators.",
                    },
                },
            )


# ---------------------------------------------------------------------------
# Validation Exception Handler
# ---------------------------------------------------------------------------


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    FastAPI override that catches input validation errors (Pydantic DTO violations)
    and maps them to a structured JSON format.

    Includes the request ID for cross-referencing with server logs.
    """
    from app.core.context import get_current_request_id

    request_id = get_current_request_id()
    errors_list: List[Dict[str, Any]] = []

    for error in exc.errors():
        field = (
            " -> ".join([str(x) for x in error["loc"][1:]])
            if len(error["loc"]) > 1
            else str(error["loc"][0])
        )
        errors_list.append(
            {"field": field, "error_type": error["type"], "message": error["msg"]}
        )

    logger.warning(
        f"Input validation failed for {request.url.path}",
        extra={
            "validation_errors": errors_list,
            "request_id": request_id,
            "path": request.url.path,
        },
    )

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "request_id": request_id,
            "error": {
                "code": "INPUT_VALIDATION_ERROR",
                "message": "API payload formatting or type bounds validation failed.",
                "details": errors_list,
            },
        },
    )
