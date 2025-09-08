"""API routes for currency conversion."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from currency_app.database import get_db
from currency_app.middleware.auth import get_user_context
from currency_app.middleware.metrics import record_currency_conversion, record_database_operation
from currency_app.models.conversion import ConversionRequest, ConversionResponse, ErrorResponse
from currency_app.models.database import ConversionHistory
from currency_app.services.currency_service import CurrencyService, InvalidCurrencyError

router = APIRouter(prefix="/api/v1", tags=["conversion"])


@router.post("/convert", response_model=ConversionResponse)
async def convert_currency(
    conversion_request: ConversionRequest, request: Request, db: Session = Depends(get_db)
) -> ConversionResponse:
    """Convert currency from one type to another.

    Args:
        conversion_request: Conversion request with amount and currencies
        request: FastAPI request object with authentication context
        db: Database session

    Returns:
        Conversion response with results

    Raises:
        HTTPException: If currency is invalid or conversion fails
    """
    # Get user context from authenticated request
    user_context = get_user_context(request)

    # Initialize currency service
    currency_service = CurrencyService()

    try:
        # Perform conversion with user context for enhanced logging
        response = currency_service.convert_currency(conversion_request, user_context)

        # Record successful conversion metrics
        record_currency_conversion(
            from_currency=response.from_currency, to_currency=response.to_currency, success=True
        )

        # Store conversion in database
        conversion_record = ConversionHistory(
            conversion_id=str(response.conversion_id),
            request_id=str(response.request_id) if response.request_id else None,
            amount=float(response.amount),
            from_currency=response.from_currency,
            to_currency=response.to_currency,
            converted_amount=float(response.converted_amount),
            exchange_rate=float(response.exchange_rate),
            account_id=user_context.account_id,
            user_id=user_context.user_id,
            conversion_timestamp=response.conversion_timestamp,
        )

        db.add(conversion_record)
        db.commit()
        db.refresh(conversion_record)

        # Record successful database operation
        record_database_operation(operation="insert", table="conversion_history", success=True)

        return response

    except InvalidCurrencyError as e:
        # Record failed conversion metrics
        record_currency_conversion(
            from_currency=conversion_request.from_currency,
            to_currency=conversion_request.to_currency,
            success=False,
        )

        error_response = ErrorResponse.create(
            code="INVALID_CURRENCY",
            message=str(e),
            details={
                "supported_currencies": ", ".join(currency_service.get_supported_currencies())
            },
            request_id=conversion_request.request_id,
        )
        raise HTTPException(status_code=400, detail=error_response.error)

    except Exception as e:
        # Record failed conversion metrics
        record_currency_conversion(
            from_currency=conversion_request.from_currency,
            to_currency=conversion_request.to_currency,
            success=False,
        )

        error_response = ErrorResponse.create(
            code="CONVERSION_ERROR",
            message="An unexpected error occurred during conversion",
            details={"error": str(e)},
            request_id=conversion_request.request_id,
        )
        raise HTTPException(status_code=500, detail=error_response.error)
