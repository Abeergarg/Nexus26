"""
Structured logging for Project Nexus26.

Provides:
  - StructuredJSONFormatter: outputs log records as single-line JSON.
  - StructuredLoggerAdapter: simplifies passing key-value context into logs.
  - get_structured_logger(): factory that returns a configured adapter.
  - log_execution_time: decorator that logs function duration_ms.
"""

import functools
import logging
import time
import json
from datetime import datetime, UTC
from typing import Any, Callable, Dict, Optional

from app.core.context import get_current_request_id


class StructuredJSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs log records as single-line JSON,
    suitable for parsing by structured logging pipelines (ELK, Cloud Logging, etc.).
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat() + "Z",
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
        }

        # Inject the current request ID from context if available
        request_id = get_current_request_id()
        if request_id:
            log_entry["request_id"] = request_id

        # Include stack trace if exception occurred
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Merge extra attributes if present
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_entry.update(record.extra_data)

        return json.dumps(log_entry)


def get_logger(name: str) -> logging.Logger:
    """Returns a preconfigured logger instance with structured JSON output."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = StructuredJSONFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


class StructuredLoggerAdapter(logging.LoggerAdapter):
    """Adapter that simplifies appending custom key-value pairs to log events."""

    def log(self, level: int, msg: Any, *args: Any, **kwargs: Any) -> None:
        extra_data = kwargs.pop("extra", {})
        merged_extra = {**self.extra, **extra_data} if self.extra else extra_data
        kwargs["extra"] = {"extra_data": merged_extra}
        super().log(level, msg, *args, **kwargs)


def get_structured_logger(
    name: str, context: Optional[Dict[str, Any]] = None
) -> StructuredLoggerAdapter:
    """
    Factory function that returns a StructuredLoggerAdapter.

    Args:
        name: Logger name (typically the module or class name).
        context: Optional dict of baseline key-value pairs appended to every log entry.

    Returns:
        A configured StructuredLoggerAdapter instance.
    """
    base_logger = get_logger(name)
    return StructuredLoggerAdapter(base_logger, context or {})


def log_execution_time(logger_name: str = "ExecutionTimer") -> Callable:
    """
    Decorator factory that measures and logs the execution duration of a function.

    Logs ``duration_ms``, ``function``, and ``module`` at INFO level.
    Works with both sync and async functions.

    Usage::

        @log_execution_time("OperationsService")
        def generate_live_operations_forecast(...):
            ...
    """
    _logger = get_structured_logger(logger_name)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                duration_ms = round((time.perf_counter() - start) * 1000, 2)
                _logger.info(
                    f"Executed {func.__name__}",
                    extra={
                        "function": func.__name__,
                        "module": func.__module__,
                        "duration_ms": duration_ms,
                    },
                )

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                duration_ms = round((time.perf_counter() - start) * 1000, 2)
                _logger.info(
                    f"Executed {func.__name__}",
                    extra={
                        "function": func.__name__,
                        "module": func.__module__,
                        "duration_ms": duration_ms,
                    },
                )

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
