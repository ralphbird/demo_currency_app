"""Logging configuration for currency conversion API."""

from common.logging_config import configure_structlog, get_logger

# Configure structlog for currency API
configure_structlog("currency-api")

# Re-export get_logger
__all__ = ["get_logger"]
