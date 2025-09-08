"""Health check endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from currency_app.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Basic health check endpoint.

    Returns:
        Health status and timestamp
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "service": "currency-conversion-api",
    }


@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)) -> dict[str, str | dict[str, str]]:
    """Detailed health check including database connectivity.

    Args:
        db: Database session

    Returns:
        Detailed health status
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "service": "currency-conversion-api",
        "checks": {},
    }

    # Test database connectivity
    try:
        from sqlalchemy import text

        db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = "healthy"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = f"unhealthy: {e!s}"

    return health_status
