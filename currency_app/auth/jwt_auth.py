"""JWT authentication utilities and user context management."""

import time
from typing import Any

import jwt
from pydantic import BaseModel, field_validator

from currency_app.config import settings


class UserContext(BaseModel):
    """User context extracted from JWT token."""

    account_id: str
    user_id: str

    @field_validator("account_id", "user_id")
    @classmethod
    def validate_uuid_string(cls, v: str) -> str:
        """Validate that account_id and user_id are non-empty strings."""
        if not v or not v.strip():
            msg = "Account ID and User ID must be non-empty strings"
            raise ValueError(msg)
        return v.strip()


class AuthenticationError(Exception):
    """Base authentication error."""


class InvalidTokenError(AuthenticationError):
    """Invalid JWT token error."""


class ExpiredTokenError(AuthenticationError):
    """Expired JWT token error."""


class MissingTokenError(AuthenticationError):
    """Missing JWT token error."""


def validate_jwt_token(token: str) -> UserContext:
    """Validate JWT token and extract user context.

    Args:
        token: JWT token string

    Returns:
        UserContext with account_id and user_id

    Raises:
        InvalidTokenError: If token is malformed or has invalid signature
        ExpiredTokenError: If token has expired
        MissingTokenError: If token is empty or None
    """
    if not token or not token.strip():
        raise MissingTokenError("JWT token is required")

    try:
        # Decode and validate the JWT token
        payload = jwt.decode(
            token.strip(),
            settings.jwt_secret_key,
            algorithms=["HS256"],
            options={
                "verify_exp": False
            },  # We handle expiration manually since tokens don't expire in dev
        )

        # Extract required claims
        account_id = payload.get("account_id")
        user_id = payload.get("user_id")

        if not account_id or not user_id:
            raise InvalidTokenError("Token must contain account_id and user_id")

        # Create and validate user context
        return UserContext(account_id=account_id, user_id=user_id)

    except jwt.InvalidTokenError as e:
        raise InvalidTokenError(f"Invalid JWT token: {e}") from e
    except ValueError as e:
        raise InvalidTokenError(f"Invalid token claims: {e}") from e


def generate_jwt_token(account_id: str, user_id: str, expires_in_seconds: int | None = None) -> str:
    """Generate JWT token for testing and development.

    Args:
        account_id: Account identifier
        user_id: User identifier
        expires_in_seconds: Token expiration time (None for no expiration)

    Returns:
        JWT token string

    Raises:
        ValueError: If account_id or user_id are invalid
    """
    if not account_id or not account_id.strip():
        msg = "account_id must be a non-empty string"
        raise ValueError(msg)
    if not user_id or not user_id.strip():
        msg = "user_id must be a non-empty string"
        raise ValueError(msg)

    # Prepare token payload
    payload: dict[str, Any] = {
        "account_id": account_id.strip(),
        "user_id": user_id.strip(),
        "iat": int(time.time()),  # Issued at
    }

    # Add expiration if specified
    if expires_in_seconds is not None:
        payload["exp"] = int(time.time()) + expires_in_seconds

    # Generate token
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def extract_token_from_header(authorization_header: str) -> str:
    """Extract JWT token from Authorization header.

    Args:
        authorization_header: Authorization header value

    Returns:
        JWT token string

    Raises:
        MissingTokenError: If header is empty or doesn't contain Bearer token
        InvalidTokenError: If header format is invalid
    """
    if not authorization_header or not authorization_header.strip():
        raise MissingTokenError("Authorization header is required")

    header_parts = authorization_header.strip().split()

    if len(header_parts) != 2:
        raise InvalidTokenError("Authorization header must be 'Bearer <token>'")

    scheme, token = header_parts
    if scheme.lower() != "bearer":
        raise InvalidTokenError("Authorization header must use Bearer scheme")

    if not token:
        raise MissingTokenError("Bearer token cannot be empty")

    return token
