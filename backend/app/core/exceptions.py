from fastapi import Request, Response
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Any, Dict, List
import traceback

from app.core.logging import get_structured_logger

logger = get_structured_logger("ExceptionGateway")


class NexusException(Exception):
    """Base exception class for Project Nexus26."""

    def __init__(self, message: str, code: str = "NEXUS_ERROR", status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class RouteCalculationError(NexusException):
    """Triggered when Dijkstra fails or constraints are unsatisfiable."""

    def __init__(self, message: str):
        super().__init__(message, code="ROUTE_CALCULATION_FAILED", status_code=400)


class WeatherAPIError(NexusException):
    """Triggered when weather fetching and all retries fail."""

    def __init__(self, message: str):
        super().__init__(message, code="WEATHER_FETCH_FAILED", status_code=502)


class GlobalExceptionMiddleware(BaseHTTPMiddleware):
    """
    Middleware that intercepts all unhandled errors, logs a structured traceback,
    and returns a clean JSON error response to avoid stack leaks.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            # Skip logging custom Nexus exceptions as severe errors
            if isinstance(exc, NexusException):
                logger.warning(
                    f"Nexus domain error intercepted: {exc.message}",
                    extra={"error_code": exc.code, "status_code": exc.status_code},
                )
                return JSONResponse(
                    status_code=exc.status_code,
                    content={
                        "success": False,
                        "error": {"code": exc.code, "message": exc.message},
                    },
                )

            # Unexpected system-level crashes
            tb = traceback.format_exc()
            logger.error(
                f"Unhandled Exception: {str(exc)}",
                extra={
                    "traceback": tb,
                    "path": request.url.path,
                    "method": request.method,
                },
            )
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected error occurred. Please consult venue administrators.",
                    },
                },
            )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    FastAPI override that catches input validation errors (Pydantic DTO violations),
    mapping them to a structured JSON format.
    """
    errors_list: List[Dict[str, Any]] = []
    for error in exc.errors():
        # Get field path (loc) e.g., body -> density
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
        extra={"validation_errors": errors_list},
    )

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": "INPUT_VALIDATION_ERROR",
                "message": "API payload formatting or type bounds validation failed.",
                "details": errors_list,
            },
        },
    )
