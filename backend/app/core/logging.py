import logging
import json
from datetime import datetime, UTC
from typing import Any, Dict


class StructuredJSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs log records as single-line JSON,
    perfect for parsing by structured logging pipelines (e.g. ELK, Cloud Logging).
    """

    def format(self, record: logging.LogRecord) -> str:
        # Standard attributes
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat() + "Z",
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
        }

        # Include stack trace if exception occurred
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Merge extra attributes if present
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_entry.update(record.extra_data)

        return json.dumps(log_entry)


def get_logger(name: str) -> logging.Logger:
    """Returns a preconfigured logger instance executing structured outputs."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if logger was already configured
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = StructuredJSONFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


class StructuredLoggerAdapter(logging.LoggerAdapter):
    """Adapter to simplify appending custom key-value pairs to log events."""

    def log(self, level: int, msg: Any, *args: Any, **kwargs: Any) -> None:
        extra_data = kwargs.pop("extra", {})
        # Merge with existing contextual data
        merged_extra = {**self.extra, **extra_data} if self.extra else extra_data
        kwargs["extra"] = {"extra_data": merged_extra}
        super().log(level, msg, *args, **kwargs)


def get_structured_logger(
    name: str, context: Dict[str, Any] = None
) -> StructuredLoggerAdapter:
    base_logger = get_logger(name)
    return StructuredLoggerAdapter(base_logger, context or {})
