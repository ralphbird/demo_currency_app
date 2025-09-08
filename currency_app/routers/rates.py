"""API routes for exchange rates."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from currency_app.database import get_db
from currency_app.middleware.metrics import record_rates_request
from currency_app.models.conversion import ErrorResponse, RatesHistoryResponse, RatesResponse
from currency_app.services.currency_service import CurrencyService
from currency_app.services.rates_history_service import RatesHistoryService

router = APIRouter(prefix="/api/v1", tags=["rates"])


@router.get("/rates", response_model=RatesResponse)
async def get_current_rates() -> RatesResponse:
    """Get current exchange rates for all supported currencies.

    Returns:
        Current exchange rates relative to USD

    Raises:
        HTTPException: If rates cannot be retrieved
    """
    try:
        # Initialize currency service
        currency_service = CurrencyService()

        # Get current rates
        result = currency_service.get_current_rates()

        # Record successful rates request
        record_rates_request(endpoint="current_rates", success=True)

        return result

    except Exception as e:
        # Record failed rates request
        record_rates_request(endpoint="current_rates", success=False)

        error_response = ErrorResponse.create(
            code="RATES_ERROR",
            message="An unexpected error occurred while retrieving rates",
            details={"error": str(e)},
        )
        raise HTTPException(status_code=500, detail=error_response.error)


@router.get("/rates/history", response_model=RatesHistoryResponse)
async def get_rates_history(
    currency: str | None = Query(None, description="Filter by specific currency code"),
    days: int = Query(7, ge=1, le=365, description="Number of days of history to retrieve"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of records"),
    db: Session = Depends(get_db),
) -> RatesHistoryResponse:
    """Get historical exchange rates with optional filtering.

    Args:
        currency: Optional currency code to filter results
        days: Number of days of history to retrieve (1-365)
        limit: Maximum number of records to return (1-10000)
        db: Database session

    Returns:
        Historical exchange rates data

    Raises:
        HTTPException: If history cannot be retrieved or parameters are invalid
    """
    try:
        # Initialize history service
        history_service = RatesHistoryService(db)

        # Validate currency if provided
        if currency:
            currency_service = CurrencyService()
            currency = currency_service.validate_currency(currency)

        # Get historical rates
        result = history_service.get_rates_history(currency=currency, days=days, limit=limit)

        # Record successful rates history request
        record_rates_request(endpoint="rates_history", success=True)

        return result

    except Exception as e:
        # Record failed rates history request
        record_rates_request(endpoint="rates_history", success=False)

        error_response = ErrorResponse.create(
            code="HISTORY_ERROR",
            message="An unexpected error occurred while retrieving rate history",
            details={"error": str(e), "currency": currency or "all", "days": str(days)},
        )
        raise HTTPException(status_code=500, detail=error_response.error)
