"""Service for managing historical exchange rates."""

import random
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal

from sqlalchemy.orm import Session

from currency_app.models.conversion import HistoricalRateInfo, RatesHistoryResponse
from currency_app.models.database import RateHistory
from currency_app.services.currency_service import CurrencyService


class RatesHistoryService:
    """Service for managing historical exchange rate data."""

    def __init__(self, db_session: Session):
        """Initialize the rates history service.

        Args:
            db_session: Database session for data operations
        """
        self.db_session = db_session
        self.currency_service = CurrencyService()

    def store_current_rates(self) -> int:
        """Store current rates as historical snapshot.

        Returns:
            Number of rates stored
        """
        current_rates = self.currency_service.get_current_rates()
        stored_count = 0

        for rate_info in current_rates.rates:
            rate_history = RateHistory(
                currency=rate_info.currency,
                rate=rate_info.rate,
                base_currency="USD",
                rate_source="simulated",
            )
            self.db_session.add(rate_history)
            stored_count += 1

        self.db_session.commit()
        return stored_count

    def generate_historical_data_for_demo(self, days_back: int = 30) -> int:
        """Generate simulated historical data for demo purposes.

        Args:
            days_back: Number of days of historical data to generate

        Returns:
            Number of historical records created
        """
        base_rates = self.currency_service.EXCHANGE_RATES
        total_records = 0

        # Generate data for each day going back
        for day_offset in range(days_back):
            # Create 4 snapshots per day (every 6 hours)
            for hour_offset in [0, 6, 12, 18]:
                timestamp = datetime.now(UTC) - timedelta(days=day_offset, hours=hour_offset)

                # Add some realistic volatility to rates
                for currency, base_rate in base_rates.items():
                    # USD should always be 1.0 as the base currency
                    if currency == "USD":
                        varied_rate = Decimal("1.000000")
                    else:
                        # Add random variation using normal distribution centered on current rate
                        # Standard deviation: 2% for most currencies, 5% for volatile ones
                        volatility_std = 0.05 if currency in ["JPY", "CNY"] else 0.02
                        # Generate normal distribution with mean=0, std=volatility_std
                        variation = random.normalvariate(0, volatility_std)
                        varied_rate = base_rate * (Decimal("1") + Decimal(str(variation)))

                        # Round to appropriate precision
                        varied_rate = varied_rate.quantize(
                            Decimal("0.000001"), rounding=ROUND_HALF_EVEN
                        )

                    rate_history = RateHistory(
                        currency=currency,
                        rate=varied_rate,
                        base_currency="USD",
                        recorded_at=timestamp,
                        rate_source="simulated",
                    )
                    self.db_session.add(rate_history)
                    total_records += 1

        self.db_session.commit()
        return total_records

    def get_rates_history(
        self, currency: str | None = None, days: int = 7, limit: int = 1000
    ) -> RatesHistoryResponse:
        """Retrieve historical exchange rates.

        Args:
            currency: Specific currency to filter by (None for all currencies)
            days: Number of days of history to retrieve
            limit: Maximum number of records to return

        Returns:
            Historical rates response with filtered data
        """
        # Calculate time range
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=days)

        # Build query
        query = self.db_session.query(RateHistory).filter(
            RateHistory.recorded_at >= start_time, RateHistory.recorded_at <= end_time
        )

        if currency:
            currency = currency.upper()
            query = query.filter(RateHistory.currency == currency)

        # Order by timestamp descending and apply limit
        query = query.order_by(RateHistory.recorded_at.desc()).limit(limit)

        # Execute query
        rate_records = query.all()

        # Convert to response format
        historical_rates = []
        for record in rate_records:
            rate_info = HistoricalRateInfo(
                currency=str(record.currency),
                rate=Decimal(str(record.rate)),
                recorded_at=record.recorded_at or datetime.now(UTC),  # type: ignore[arg-type]
                base_currency=str(record.base_currency),
                rate_source=str(record.rate_source),
            )
            historical_rates.append(rate_info)

        # Calculate period information
        if historical_rates:
            actual_start = min(rate.recorded_at for rate in historical_rates)
            actual_end = max(rate.recorded_at for rate in historical_rates)
        else:
            actual_start = start_time
            actual_end = end_time

        return RatesHistoryResponse(
            currency=currency,
            rates=historical_rates,
            period={"start": actual_start, "end": actual_end},
            total_records=len(historical_rates),
            base_currency="USD",
        )

    def get_currency_history_for_chart(
        self, currency: str, days: int = 7
    ) -> list[dict[str, str | float]]:
        """Get currency history formatted for charting.

        Args:
            currency: Currency code to get history for
            days: Number of days of history

        Returns:
            List of data points for charting
        """
        history = self.get_rates_history(currency=currency, days=days)

        chart_data = []
        for rate_info in reversed(history.rates):  # Reverse for chronological order
            chart_data.append(
                {
                    "timestamp": rate_info.recorded_at.isoformat(),
                    "rate": float(rate_info.rate),
                    "currency": rate_info.currency,
                }
            )

        return chart_data

    def get_rate_statistics(self, currency: str, days: int = 30) -> dict[str, float]:
        """Get statistical summary for a currency over time period.

        Args:
            currency: Currency code to analyze
            days: Number of days to analyze

        Returns:
            Dictionary with statistical measures
        """
        history = self.get_rates_history(currency=currency, days=days)

        if not history.rates:
            return {
                "min_rate": 0.0,
                "max_rate": 0.0,
                "avg_rate": 0.0,
                "current_rate": 0.0,
                "change_percent": 0.0,
                "volatility": 0.0,
                "total_records": 0,
            }

        rates = [float(rate.rate) for rate in history.rates]
        current_rate = rates[0]  # Most recent (first in desc order)
        oldest_rate = rates[-1]  # Oldest rate

        min_rate = min(rates)
        max_rate = max(rates)
        avg_rate = sum(rates) / len(rates)

        # Calculate change percentage
        change_percent = 0.0
        if oldest_rate != 0:
            change_percent = ((current_rate - oldest_rate) / oldest_rate) * 100

        # Simple volatility measure (standard deviation)
        if len(rates) > 1:
            variance = sum((rate - avg_rate) ** 2 for rate in rates) / len(rates)
            volatility = variance**0.5
        else:
            volatility = 0.0

        return {
            "min_rate": min_rate,
            "max_rate": max_rate,
            "avg_rate": avg_rate,
            "current_rate": current_rate,
            "change_percent": change_percent,
            "volatility": volatility,
            "total_records": len(rates),
        }
