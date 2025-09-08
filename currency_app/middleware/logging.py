"""Logging middleware for HTTP request/response tracking."""

import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware

from currency_app.logging_config import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log HTTP requests and responses using structlog context binding."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details.

        Args:
            request: The incoming request
            call_next: The next middleware/route handler

        Returns:
            The response from downstream handlers
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())

        # Extract request details
        method = request.method
        url = str(request.url)
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")

        # Bind initial request context to logger
        request_logger = logger.bind(
            request_id=request_id,
            method=method,
            endpoint=url,
            client_ip=client_ip,
            user_agent=user_agent,
        )

        # Start timer
        start_time = time.time()

        # Log incoming request
        request_logger.info(f"Incoming request: {method} {url}")

        # Add request ID and logger to request state for use in route handlers
        request.state.request_id = request_id
        request.state.logger = request_logger

        try:
            # Process request
            response = await call_next(request)

            # Calculate response time
            response_time_ms = round((time.time() - start_time) * 1000, 2)

            # After authentication, capture user context if available
            user_context_fields = {}
            if hasattr(request.state, "user_context") and request.state.user_context:
                user_context_fields.update(
                    {
                        "user_id": request.state.user_context.user_id,
                        "account_id": request.state.user_context.account_id,
                    }
                )
                # Bind user context to logger for complete request lifecycle logging
                request_logger = request_logger.bind(**user_context_fields)

                # Add user context to current OpenTelemetry span for tracing
                current_span = trace.get_current_span()
                if current_span.is_recording():
                    current_span.set_attribute("user.id", request.state.user_context.user_id)
                    current_span.set_attribute(
                        "user.account_id", request.state.user_context.account_id
                    )

            # Log response with additional context including user info when available
            request_logger.info(
                f"Request completed: {method} {url} - {response.status_code}",
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                **user_context_fields,
            )

            return response

        except Exception as e:
            # Calculate response time for errors
            response_time_ms = round((time.time() - start_time) * 1000, 2)

            # Capture user context if available for error logging
            user_context_fields = {}
            if hasattr(request.state, "user_context") and request.state.user_context:
                user_context_fields.update(
                    {
                        "user_id": request.state.user_context.user_id,
                        "account_id": request.state.user_context.account_id,
                    }
                )
                # Bind user context to logger for error reporting
                request_logger = request_logger.bind(**user_context_fields)

                # Add user context to current OpenTelemetry span for error tracing
                current_span = trace.get_current_span()
                if current_span.is_recording():
                    current_span.set_attribute("user.id", request.state.user_context.user_id)
                    current_span.set_attribute(
                        "user.account_id", request.state.user_context.account_id
                    )

            # Log error with additional context including user info and exception info
            request_logger.error(
                f"Request failed: {method} {url} - {e!s}",
                response_time_ms=response_time_ms,
                exc_info=True,
                **user_context_fields,
            )

            # Re-raise the exception
            raise

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request.

        Args:
            request: The HTTP request

        Returns:
            Client IP address
        """
        # Check for forwarded headers (for load balancers/proxies)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        forwarded_host = request.headers.get("x-forwarded-host")
        if forwarded_host:
            return forwarded_host

        # Fall back to direct client
        if request.client:
            return request.client.host

        return "unknown"
