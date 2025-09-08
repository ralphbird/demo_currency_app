"""JWT Authentication middleware for FastAPI."""

from typing import ClassVar

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from currency_app.auth.jwt_auth import (
    AuthenticationError,
    ExpiredTokenError,
    InvalidTokenError,
    MissingTokenError,
    UserContext,
    extract_token_from_header,
    validate_jwt_token,
)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware to handle JWT authentication for all requests."""

    # Paths that don't require authentication
    EXCLUDED_PATHS: ClassVar[set[str]] = {
        "/",
        "/health",
        "/health/",
        "/metrics",
        "/metrics/",
        "/docs",
        "/docs/",
        "/redoc",
        "/redoc/",
        "/openapi.json",
        "/api/v1/rates",
        "/api/v1/rates/",
        "/api/v1/rates/history",
        "/api/v1/rates/history/",
    }

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with JWT authentication.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler

        Returns:
            HTTP response

        Raises:
            HTTPException: 401 if authentication fails
        """
        # Skip authentication for excluded paths
        path = request.url.path
        if (
            path in self.EXCLUDED_PATHS
            or path.startswith(("/health", "/api/v1/rates"))
            or path == "/api"
        ):
            return await call_next(request)

        try:
            # Extract Authorization header
            authorization_header = request.headers.get("authorization", "")

            # Extract token from header
            token = extract_token_from_header(authorization_header)

            # Validate token and get user context
            user_context = validate_jwt_token(token)

            # Store user context in request state
            request.state.user_context = user_context

            # Continue with request processing
            return await call_next(request)

        except MissingTokenError:
            return JSONResponse(
                status_code=401, content={"detail": "Missing or invalid Authorization header"}
            )

        except (InvalidTokenError, ExpiredTokenError) as e:
            return JSONResponse(status_code=401, content={"detail": str(e)})

        except AuthenticationError as e:
            return JSONResponse(status_code=401, content={"detail": f"Authentication failed: {e}"})


def get_user_context(request: Request) -> UserContext:
    """Get user context from request state.

    Args:
        request: FastAPI request object

    Returns:
        UserContext with account_id and user_id

    Raises:
        HTTPException: 401 if no user context found
    """
    if not hasattr(request.state, "user_context"):
        raise HTTPException(status_code=401, detail="No authentication context found")

    return request.state.user_context
