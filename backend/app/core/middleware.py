"""
Custom Starlette/FastAPI middleware for Project Nexus26.

Provides three middleware components:
  - RequestIDMiddleware: Generates a unique UUID per request and propagates it.
  - RequestLoggingMiddleware: Logs method, path, status, and duration for every request.
  - RateLimitMiddleware: Per-IP sliding window rate limiter (in-memory).
"""

import time
import uuid
from collections import defaultdict, deque
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.constants import RATE_LIMIT_REQUESTS_PER_MINUTE, RATE_LIMIT_WINDOW_SECONDS
from app.core.context import get_current_request_id, request_id_var
from app.core.logging import get_structured_logger

logger = get_structured_logger("Middleware")


# ---------------------------------------------------------------------------
# Request ID Middleware
# ---------------------------------------------------------------------------
class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Generates a unique UUID4 for every incoming request.

    - Reads ``X-Request-ID`` from the incoming request if provided by upstream.
    - Stores the ID in a ``ContextVar`` for use in logging throughout the stack.
    - Adds ``X-Request-ID`` to every outgoing response.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = request_id
        return response


# ---------------------------------------------------------------------------
# Request Logging Middleware
# ---------------------------------------------------------------------------
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every HTTP request with method, path, status code, and duration.

    Log level is INFO for 2xx/3xx, WARNING for 4xx, ERROR for 5xx.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        log_extra = {
            "request_id": get_current_request_id(),
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "client_ip": request.client.host if request.client else "unknown",
        }

        if response.status_code >= 500:
            logger.error("Request completed with server error", extra=log_extra)
        elif response.status_code >= 400:
            logger.warning("Request completed with client error", extra=log_extra)
        else:
            logger.info("Request completed", extra=log_extra)

        return response


# ---------------------------------------------------------------------------
# Rate Limit Middleware
# ---------------------------------------------------------------------------
class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Per-IP sliding window rate limiter using an in-memory deque.

    Allows up to ``RATE_LIMIT_REQUESTS_PER_MINUTE`` requests per IP within
    a ``RATE_LIMIT_WINDOW_SECONDS`` rolling window. Health check endpoints
    are excluded from rate limiting.

    Returns HTTP 429 with a ``Retry-After`` header when the limit is exceeded.
    """

    EXCLUDED_PATHS: frozenset = frozenset({"/health/live", "/health/ready", "/"})

    def __init__(self, app) -> None:
        super().__init__(app)
        # Maps client IP -> deque of timestamps of recent requests
        self._windows: dict = defaultdict(deque)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = self._windows[client_ip]

        # Evict timestamps outside the rolling window
        while window and window[0] < now - RATE_LIMIT_WINDOW_SECONDS:
            window.popleft()

        if len(window) >= RATE_LIMIT_REQUESTS_PER_MINUTE:
            retry_after = int(RATE_LIMIT_WINDOW_SECONDS - (now - window[0]))
            logger.warning(
                "Rate limit exceeded",
                extra={
                    "client_ip": client_ip,
                    "request_count": len(window),
                    "path": request.url.path,
                    "request_id": get_current_request_id(),
                },
            )
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(max(retry_after, 1))},
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": (
                            f"Too many requests. Limit: {RATE_LIMIT_REQUESTS_PER_MINUTE} "
                            f"per {RATE_LIMIT_WINDOW_SECONDS}s. "
                            f"Retry after {max(retry_after, 1)}s."
                        ),
                    },
                },
            )

        window.append(now)
        return await call_next(request)
