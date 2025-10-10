"""Prometheus metrics middleware for FastAPI."""

import re
import time
from collections.abc import Callable

from fastapi import Request, Response
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

# Prometheus metrics
REQUEST_COUNT = Counter(
    "http_requests_total", "Total number of HTTP requests", ["method", "endpoint", "status_code"]
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds", "HTTP request duration in seconds", ["method", "endpoint"]
)

IN_PROGRESS_REQUESTS = Gauge(
    "http_requests_in_progress", "Number of HTTP requests currently being processed"
)

# Application-specific metrics
CURRENCY_CONVERSIONS_TOTAL = Counter(
    "currency_conversions_total",
    "Total number of currency conversions performed",
    ["from_currency", "to_currency", "status"],
)

RATES_REQUESTS_TOTAL = Counter(
    "rates_requests_total", "Total number of exchange rates requests", ["endpoint", "status"]
)

DATABASE_OPERATIONS_TOTAL = Counter(
    "database_operations_total",
    "Total number of database operations",
    ["operation", "table", "status"],
)

DATABASE_CONNECTION_POOL_SIZE = Gauge(
    "database_connection_pool_size", "Configured database connection pool size"
)

DATABASE_CONNECTION_POOL_ACTIVE = Gauge(
    "database_connection_pool_active", "Number of active database connections"
)

DATABASE_CONNECTION_POOL_CHECKED_OUT = Gauge(
    "database_connection_pool_checked_out", "Number of checked out database connections"
)

DATABASE_CONNECTION_TIMEOUTS = Counter(
    "database_connection_timeouts_total", "Total number of database connection timeouts"
)

DATABASE_QUERY_DURATION = Histogram(
    "database_query_duration_seconds",
    "Database query duration in seconds",
    ["operation", "table"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

DATABASE_CONNECTION_ERRORS = Counter(
    "database_connection_errors_total", "Total number of database connection errors", ["error_type"]
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics for HTTP requests."""

    def __init__(self, app):
        """Initialize the middleware."""
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics."""
        # Skip metrics endpoint to avoid recursion
        if request.url.path == "/metrics":
            return await call_next(request)

        # Extract route pattern for consistent labeling
        endpoint = self._get_endpoint_pattern(request)
        method = request.method

        # Track in-progress requests
        IN_PROGRESS_REQUESTS.inc()

        # Start timing
        start_time = time.time()

        try:
            # Process request
            response = await call_next(request)
            status_code = str(response.status_code)

            # Record successful request
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status_code).inc()

            return response

        except Exception:
            # Record failed request
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code="500").inc()
            raise

        finally:
            # Record request duration
            duration = time.time() - start_time
            REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)

            # Decrement in-progress requests
            IN_PROGRESS_REQUESTS.dec()

    def _get_endpoint_pattern(self, request: Request) -> str:
        """Extract endpoint pattern from request for consistent labeling."""
        # Try to get the route pattern from FastAPI
        if hasattr(request, "scope") and "route" in request.scope:
            route = request.scope["route"]
            if hasattr(route, "path"):
                return route.path

        # Fallback to actual path, but normalize IDs
        path = request.url.path

        # Replace common ID patterns with placeholders for better grouping
        # Replace UUIDs
        path = re.sub(
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "/{uuid}", path
        )
        # Replace numeric IDs
        return re.sub(r"/\d+", "/{id}", path)


def get_metrics() -> str:
    """Get current metrics in Prometheus format."""
    return generate_latest().decode("utf-8")


# Utility functions for application-specific metrics
def record_currency_conversion(from_currency: str, to_currency: str, *, success: bool = True):
    """Record currency conversion metrics."""
    status = "success" if success else "error"
    CURRENCY_CONVERSIONS_TOTAL.labels(
        from_currency=from_currency, to_currency=to_currency, status=status
    ).inc()


def record_rates_request(endpoint: str, *, success: bool = True):
    """Record exchange rates request metrics."""
    status = "success" if success else "error"
    RATES_REQUESTS_TOTAL.labels(endpoint=endpoint, status=status).inc()


def record_database_operation(operation: str, table: str, *, success: bool = True):
    """Record database operation metrics."""
    status = "success" if success else "error"
    DATABASE_OPERATIONS_TOTAL.labels(operation=operation, table=table, status=status).inc()


def record_database_query_duration(operation: str, table: str, duration: float):
    """Record database query duration."""
    DATABASE_QUERY_DURATION.labels(operation=operation, table=table).observe(duration)


def record_database_connection_timeout():
    """Record database connection timeout."""
    DATABASE_CONNECTION_TIMEOUTS.inc()


def record_database_connection_error(error_type: str):
    """Record database connection error."""
    DATABASE_CONNECTION_ERRORS.labels(error_type=error_type).inc()


def update_connection_pool_metrics(engine):
    """Update connection pool metrics from SQLAlchemy engine."""
    try:
        pool = engine.pool

        # Set pool size
        DATABASE_CONNECTION_POOL_SIZE.set(pool.size())

        # Set active connections (checked out)
        DATABASE_CONNECTION_POOL_CHECKED_OUT.set(pool.checkedout())

        # Calculate available connections
        active_connections = pool.checkedout()
        DATABASE_CONNECTION_POOL_ACTIVE.set(active_connections)

    except AttributeError:
        # Handle case where pool doesn't support these methods (e.g., SQLite)
        pass
    except Exception as e:
        # Log error but don't fail
        record_database_connection_error(f"pool_metrics_error_{type(e).__name__}")
