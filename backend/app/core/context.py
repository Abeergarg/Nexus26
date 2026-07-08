"""
Shared context variables for Project Nexus26.

This module defines low-level ContextVar primitives that must be importable
by both the logging and middleware modules without creating circular imports.
"""

from contextvars import ContextVar

# Carries the current request's UUID through the async call stack.
# Set by RequestIDMiddleware; read by StructuredJSONFormatter and exception handlers.
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_current_request_id() -> str:
    """Returns the request ID bound to the current async context, or an empty string."""
    return request_id_var.get()
