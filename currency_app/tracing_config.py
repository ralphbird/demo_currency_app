"""OpenTelemetry tracing configuration for currency conversion API."""

import os
import sys
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import StatusCode


def configure_tracing(
    service_name: str = "currency-api",
    jaeger_endpoint: str | None = None,
    *,
    enable_console_export: bool = False,
) -> None:
    """Configure OpenTelemetry tracing for the application.

    Args:
        service_name: Name of the service for tracing
        jaeger_endpoint: Jaeger collector endpoint URL
        enable_console_export: Whether to enable console span export for debugging
    """
    # Create resource with service information
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": os.getenv("SERVICE_VERSION", "1.0.0"),
            "deployment.environment": os.getenv("ENVIRONMENT", "development"),
        }
    )

    # Initialize tracer provider
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)

    # Configure OTLP exporter for Jaeger if endpoint provided
    jaeger_endpoint = jaeger_endpoint or os.getenv("JAEGER_ENDPOINT")
    if jaeger_endpoint:
        # For OTLP, use port 4317 (default OTLP gRPC port)
        otlp_endpoint = jaeger_endpoint.replace(":14250", ":4317")
        otlp_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            insecure=True,  # For development
        )
        span_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(span_processor)

    # Add console exporter for development/debugging (but not during testing)
    is_testing = "pytest" in sys.modules or os.getenv("PYTEST_CURRENT_TEST")
    if not is_testing and (
        enable_console_export or os.getenv("OTEL_CONSOLE_EXPORT", "").lower() == "true"
    ):
        console_exporter = ConsoleSpanExporter()
        console_processor = BatchSpanProcessor(console_exporter)
        tracer_provider.add_span_processor(console_processor)


def instrument_application() -> None:
    """Instrument the application with OpenTelemetry auto-instrumentation."""
    # Instrument FastAPI
    FastAPIInstrumentor().instrument()

    # Instrument SQLAlchemy
    SQLAlchemyInstrumentor().instrument()

    # Instrument requests library
    RequestsInstrumentor().instrument()


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer instance for the given name.

    Args:
        name: Name for the tracer, typically __name__

    Returns:
        OpenTelemetry tracer instance
    """
    return trace.get_tracer(name)


def get_current_span() -> trace.Span | None:
    """Get the current active span.

    Returns:
        Current span or None if no active span
    """
    return trace.get_current_span()


def add_span_attributes(attributes: dict[str, Any]) -> None:
    """Add attributes to the current span.

    Args:
        attributes: Dictionary of attributes to add to current span
    """
    current_span = get_current_span()
    if current_span:
        for key, value in attributes.items():
            current_span.set_attribute(key, value)


def add_span_event(name: str, attributes: dict[str, Any] | None = None) -> None:
    """Add an event to the current span.

    Args:
        name: Event name
        attributes: Optional event attributes
    """
    current_span = get_current_span()
    if current_span:
        current_span.add_event(name, attributes or {})


def set_span_status(status_code: StatusCode, description: str | None = None) -> None:
    """Set the status of the current span.

    Args:
        status_code: Status code (OK, ERROR, UNSET)
        description: Optional status description
    """
    current_span = get_current_span()
    if current_span:
        current_span.set_status(trace.Status(status_code, description))
