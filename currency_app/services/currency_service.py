"""Currency conversion service with simulated exchange rates."""

from datetime import UTC, datetime
from decimal import ROUND_HALF_EVEN, Decimal
from typing import ClassVar

from currency_app.auth.jwt_auth import UserContext
from currency_app.logging_config import get_logger
from currency_app.models.conversion import (
    ConversionRequest,
    ConversionResponse,
    RateInfo,
    RatesResponse,
)
from currency_app.tracing_config import add_span_event, get_tracer

logger = get_logger(__name__)
tracer = get_tracer(__name__)


class InvalidCurrencyError(Exception):
    """Raised when an invalid currency code is provided."""


class CurrencyService:
    """Service for currency conversion with simulated exchange rates."""

    # Static exchange rates relative to USD (as of a simulated snapshot)
    EXCHANGE_RATES: ClassVar[dict[str, Decimal]] = {
        "USD": Decimal("1.0000"),
        "EUR": Decimal("0.8523"),
        "GBP": Decimal("0.7891"),
        "JPY": Decimal("110.4500"),
        "AUD": Decimal("1.3456"),
        "CAD": Decimal("1.2567"),
        "CHF": Decimal("0.9234"),
        "CNY": Decimal("6.4521"),
        "SEK": Decimal("8.7654"),
        "NZD": Decimal("1.4321"),
    }

    SUPPORTED_CURRENCIES: ClassVar[set[str]] = set(EXCHANGE_RATES.keys())

    def __init__(self):
        """Initialize the currency service."""
        self.rate_timestamp = datetime.now(UTC)

    def validate_currency(self, currency_code: str) -> str:
        """Validate and normalize currency code.

        Args:
            currency_code: Currency code to validate

        Returns:
            Normalized currency code

        Raises:
            InvalidCurrencyError: If currency is not supported
        """
        with tracer.start_as_current_span("validate_currency") as span:
            span.set_attribute("currency.code.original", currency_code)

            normalized_code = currency_code.upper()
            span.set_attribute("currency.code.normalized", normalized_code)

            if normalized_code not in self.SUPPORTED_CURRENCIES:
                span.set_attribute("currency.validation.result", "invalid")
                add_span_event(
                    "currency_validation_failed",
                    {
                        "currency_code": currency_code,
                        "supported_currencies": sorted(self.SUPPORTED_CURRENCIES),
                    },
                )
                raise InvalidCurrencyError(
                    f"Currency code '{currency_code}' is not supported. "
                    f"Supported currencies: {sorted(self.SUPPORTED_CURRENCIES)}"
                )

            span.set_attribute("currency.validation.result", "valid")
            add_span_event("currency_validation_success")
            return normalized_code

    def get_exchange_rate(self, from_currency: str, to_currency: str) -> Decimal:
        """Get exchange rate between two currencies.

        Args:
            from_currency: Source currency code
            to_currency: Target currency code

        Returns:
            Exchange rate from source to target currency

        Raises:
            InvalidCurrencyError: If either currency is not supported
        """
        with tracer.start_as_current_span("get_exchange_rate") as span:
            span.set_attribute("currency.from", from_currency)
            span.set_attribute("currency.to", to_currency)

            from_currency = self.validate_currency(from_currency)
            to_currency = self.validate_currency(to_currency)

            span.set_attribute("currency.from.normalized", from_currency)
            span.set_attribute("currency.to.normalized", to_currency)

            if from_currency == to_currency:
                span.set_attribute("exchange_rate.type", "same_currency")
                span.set_attribute("exchange_rate.value", 1.0)
                add_span_event("same_currency_conversion")
                return Decimal("1.0000")

            # Convert via USD (all rates are relative to USD)
            from_usd_rate = self.EXCHANGE_RATES[from_currency]
            to_usd_rate = self.EXCHANGE_RATES[to_currency]

            span.set_attribute("exchange_rate.from_usd", float(from_usd_rate))
            span.set_attribute("exchange_rate.to_usd", float(to_usd_rate))
            span.set_attribute("exchange_rate.type", "cross_currency")

            # Calculate cross rate: (1 / from_usd_rate) * to_usd_rate
            exchange_rate = to_usd_rate / from_usd_rate

            # Round to 6 decimal places for rate precision
            exchange_rate = exchange_rate.quantize(Decimal("0.000001"), rounding=ROUND_HALF_EVEN)

            span.set_attribute("exchange_rate.value", float(exchange_rate))
            add_span_event(
                "exchange_rate_calculated",
                {
                    "from_currency": from_currency,
                    "to_currency": to_currency,
                    "rate": float(exchange_rate),
                },
            )

            return exchange_rate

    def convert_currency(
        self, request: ConversionRequest, user_context: UserContext | None = None
    ) -> ConversionResponse:
        """Convert currency based on request.

        Args:
            request: Conversion request with amount and currencies
            user_context: Optional user context for logging and tracing

        Returns:
            Conversion response with results

        Raises:
            InvalidCurrencyError: If currencies are not supported
        """
        with tracer.start_as_current_span("convert_currency") as span:
            # Set request attributes
            span.set_attribute("conversion.request_id", str(request.request_id))
            span.set_attribute("conversion.amount", float(request.amount))
            span.set_attribute("conversion.from_currency", request.from_currency)
            span.set_attribute("conversion.to_currency", request.to_currency)

            # Bind context for this conversion operation
            logger_context = {
                "request_id": request.request_id,
                "from_currency": request.from_currency,
                "to_currency": request.to_currency,
                "amount": str(request.amount),
            }

            # Add user context if available
            if user_context:
                logger_context.update(
                    {
                        "user_id": user_context.user_id,
                        "account_id": user_context.account_id,
                    }
                )
                # Also add to span attributes for tracing
                span.set_attribute("user.id", user_context.user_id)
                span.set_attribute("user.account_id", user_context.account_id)

            conversion_logger = logger.bind(**logger_context)

            conversion_logger.info(
                f"Converting currency: {request.amount} {request.from_currency} -> {request.to_currency}"
            )

            try:
                add_span_event(
                    "conversion_started",
                    {"request_id": str(request.request_id), "amount": float(request.amount)},
                )

                # Validate currencies
                from_currency = self.validate_currency(request.from_currency)
                to_currency = self.validate_currency(request.to_currency)

                # Get exchange rate
                exchange_rate = self.get_exchange_rate(from_currency, to_currency)

                # Calculate converted amount
                converted_amount = request.amount * exchange_rate

                # Round to 2 decimal places for currency amounts (banker's rounding)
                converted_amount = converted_amount.quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_EVEN
                )

                # Set result attributes
                span.set_attribute("conversion.result.exchange_rate", float(exchange_rate))
                span.set_attribute("conversion.result.converted_amount", float(converted_amount))
                span.set_attribute("conversion.status", "success")

                conversion_logger.info(
                    f"Currency conversion completed: {request.amount} {from_currency} = {converted_amount} {to_currency} (rate: {exchange_rate})",
                    converted_amount=str(converted_amount),
                    exchange_rate=str(exchange_rate),
                )

                add_span_event(
                    "conversion_completed",
                    {
                        "converted_amount": float(converted_amount),
                        "exchange_rate": float(exchange_rate),
                    },
                )

            except InvalidCurrencyError as e:
                span.set_attribute("conversion.status", "error")
                span.set_attribute("conversion.error.type", "invalid_currency")
                span.set_attribute("conversion.error.message", str(e))

                add_span_event(
                    "conversion_failed", {"error_type": "invalid_currency", "error_message": str(e)}
                )

                conversion_logger.warning(f"Currency conversion failed - invalid currency: {e!s}")
                raise
            except Exception as e:
                span.set_attribute("conversion.status", "error")
                span.set_attribute("conversion.error.type", "unexpected")
                span.set_attribute("conversion.error.message", str(e))

                add_span_event(
                    "conversion_failed", {"error_type": "unexpected", "error_message": str(e)}
                )

                conversion_logger.error(
                    f"Currency conversion failed unexpectedly: {e!s}",
                    exc_info=True,
                )
                raise

            # Create response
            return ConversionResponse(
                request_id=request.request_id,
                amount=request.amount,
                from_currency=from_currency,
                to_currency=to_currency,
                converted_amount=converted_amount,
                exchange_rate=exchange_rate,
                rate_timestamp=self.rate_timestamp,
            )

    def get_supported_currencies(self) -> list[str]:
        """Get list of supported currency codes.

        Returns:
            Sorted list of supported currency codes
        """
        return sorted(self.SUPPORTED_CURRENCIES)

    def get_current_rates(self) -> RatesResponse:
        """Get all current exchange rates.

        Returns:
            Response containing all current exchange rates relative to USD
        """
        with tracer.start_as_current_span("get_current_rates") as span:
            span.set_attribute("rates.count", len(self.EXCHANGE_RATES))
            span.set_attribute("rates.base_currency", "USD")

            add_span_event(
                "rates_retrieval_started", {"currencies_count": len(self.EXCHANGE_RATES)}
            )

            rates = []
            for currency, rate in sorted(self.EXCHANGE_RATES.items()):
                rate_info = RateInfo(
                    currency=currency,
                    rate=rate,
                    last_updated=self.rate_timestamp,
                )
                rates.append(rate_info)

            span.set_attribute("rates.timestamp", self.rate_timestamp.isoformat())
            add_span_event("rates_retrieval_completed", {"rates_returned": len(rates)})

            return RatesResponse(rates=rates)
