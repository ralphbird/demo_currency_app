"""Main FastAPI application for currency conversion API."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Response

from currency_app.database import create_tables
from currency_app.logging_config import get_logger
from currency_app.middleware.auth import AuthenticationMiddleware
from currency_app.middleware.logging import LoggingMiddleware
from currency_app.middleware.metrics import PrometheusMiddleware, get_metrics
from currency_app.routers import conversion, debug, health, home, rates
from currency_app.tracing_config import configure_tracing, instrument_application

# Structlog is configured automatically when logging_config is imported
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup: Initialize tracing and create database tables
    logger.info("Starting Currency API application")

    # Configure tracing
    try:
        configure_tracing(
            service_name="currency-api",
            enable_console_export=True,  # Enable for development
        )
        instrument_application()
        logger.info("OpenTelemetry tracing configured successfully")
    except Exception:
        logger.error("Failed to configure tracing", exc_info=True)
        # Don't fail startup for tracing issues

    # Create database tables
    try:
        create_tables()
        logger.info("Database tables created successfully")
    except Exception:
        logger.error("Failed to create database tables", exc_info=True)
        raise

    logger.info("Currency API application started successfully")
    yield

    # Shutdown: Could add cleanup here if needed
    logger.info("Shutting down Currency API application")


# Create FastAPI application
app = FastAPI(
    title="Currency Conversion API",
    description="A demo API for currency conversion with debugging capabilities",
    version="0.1.0",
    lifespan=lifespan,
)

# Add middleware (order matters - auth first, then logging to capture all requests)
app.add_middleware(AuthenticationMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(PrometheusMiddleware)

# Include routers
app.include_router(home.router)
app.include_router(health.router)
app.include_router(conversion.router)
app.include_router(rates.router)
app.include_router(debug.router)


@app.get("/api")
async def api_info() -> dict[str, str | dict[str, str]]:
    """API information endpoint.

    Returns:
        API information and available endpoints
    """
    return {
        "message": "Currency Conversion API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "convert": "/api/v1/convert",
            "rates": "/api/v1/rates",
            "rates_history": "/api/v1/rates/history",
            "metrics": "/metrics",
        },
    }


@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint.

    Returns:
        Prometheus metrics in text format
    """
    return Response(content=get_metrics(), media_type="text/plain")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("currency_app.main:app", host="0.0.0.0", port=8000, reload=True)
