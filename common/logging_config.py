"""Shared logging configuration using structlog for all services."""

import sys
from typing import Any

import structlog
from opentelemetry import trace


def add_service_name(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Add service name to log entries.

    Args:
        logger: The logger instance (unused)
        method_name: The method name (unused)
        event_dict: The log event dictionary

    Returns:
        Updated event dictionary with service name
    """
    # Default service name, can be overridden during configuration
    if "service" not in event_dict:
        event_dict["service"] = "unknown"
    return event_dict


def add_trace_context(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Add OpenTelemetry trace context to log entries.

    Args:
        logger: The logger instance (unused)
        method_name: The method name (unused)
        event_dict: The log event dictionary

    Returns:
        Updated event dictionary with trace context
    """
    span_context = trace.get_current_span().get_span_context()
    if span_context.is_valid:
        event_dict["trace_id"] = f"{span_context.trace_id:032x}"
        event_dict["span_id"] = f"{span_context.span_id:016x}"
    return event_dict


def configure_structlog(service_name: str) -> None:
    """Configure structlog for a specific service.

    Args:
        service_name: Name of the service (e.g., 'currency-api')
    """
    # Configure processors that transform log entries
    processors = [
        # Filter by log level
        structlog.stdlib.filter_by_level,
        # Add logger name
        structlog.stdlib.add_logger_name,
        # Add log level
        structlog.stdlib.add_log_level,
        # Add ISO timestamp
        structlog.processors.TimeStamper(fmt="iso"),
        # Add service name
        add_service_name,
        # Add OpenTelemetry trace context
        add_trace_context,
        # Format stack traces nicely
        structlog.processors.format_exc_info,
        # Convert to JSON
        structlog.processors.JSONRenderer(),
    ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to work with structlog
    import logging

    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # Use plain formatter since structlog handles formatting
    plain_formatter = logging.Formatter("%(message)s")
    console_handler.setFormatter(plain_formatter)

    # Add handler to root logger
    root_logger.addHandler(console_handler)

    # Configure specific loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)

    # Set default service name in context
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(service=service_name)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structlog logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)
