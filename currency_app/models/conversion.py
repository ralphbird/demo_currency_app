"""Pydantic models for currency conversion."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import uuid_utils.compat as uuid
from pydantic import BaseModel, Field, field_validator


class ConversionRequest(BaseModel):
    """Request model for currency conversion."""

    amount: Decimal = Field(
        ...,
        gt=0,
        le=Decimal("99999999999999.99"),
        description="Amount to convert (max 99.99 trillion)",
    )
    from_currency: str = Field(..., min_length=3, max_length=3, description="Source currency code")
    to_currency: str = Field(..., min_length=3, max_length=3, description="Target currency code")
    request_id: UUID = Field(
        default_factory=uuid.uuid7, description="Request ID (auto-generated if not provided)"
    )

    @field_validator("from_currency", "to_currency")
    @classmethod
    def validate_currency_code(cls, v):
        """Validate currency codes are uppercase."""
        return v.upper()


class ConversionResponse(BaseModel):
    """Response model for currency conversion."""

    conversion_id: UUID = Field(default_factory=uuid.uuid7, description="Unique conversion ID")
    request_id: UUID = Field(..., description="Request ID from input")
    amount: Decimal = Field(..., description="Original amount")
    from_currency: str = Field(..., description="Source currency code")
    to_currency: str = Field(..., description="Target currency code")
    converted_amount: Decimal = Field(..., description="Converted amount")
    exchange_rate: Decimal = Field(..., description="Exchange rate used")
    rate_timestamp: datetime = Field(..., description="When the rate was last updated")
    conversion_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When conversion was performed",
    )
    metadata: dict[str, str] = Field(
        default_factory=lambda: {
            "rate_source": "simulated",
            "calculation_method": "direct",
            "precision": "4",
        },
        description="Additional metadata about the conversion",
    )


class ErrorResponse(BaseModel):
    """Error response model."""

    error: dict[str, str | dict[str, str]] = Field(..., description="Error details")

    @classmethod
    def create(
        cls,
        code: str,
        message: str,
        details: dict[str, str] | None = None,
        request_id: UUID | None = None,
    ) -> "ErrorResponse":
        """Create an error response."""
        error_data: dict[str, str | dict[str, str]] = {
            "code": code,
            "message": message,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        if details:
            error_data["details"] = details
        if request_id:
            error_data["request_id"] = str(request_id)

        return cls(error=error_data)


class RateInfo(BaseModel):
    """Individual exchange rate information."""

    currency: str = Field(..., description="Currency code")
    rate: Decimal = Field(..., description="Exchange rate relative to USD")
    last_updated: datetime = Field(..., description="When this rate was last updated")


class RatesResponse(BaseModel):
    """Response model for current exchange rates."""

    base_currency: str = Field(default="USD", description="Base currency for all rates")
    rates: list[RateInfo] = Field(..., description="List of exchange rates")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When rates were retrieved",
    )
    metadata: dict[str, str] = Field(
        default_factory=lambda: {
            "rate_source": "simulated",
            "total_currencies": "10",
        },
        description="Additional metadata about the rates",
    )


class HistoricalRateInfo(BaseModel):
    """Historical exchange rate information with timestamp."""

    currency: str = Field(..., description="Currency code")
    rate: Decimal = Field(..., description="Exchange rate relative to base currency")
    recorded_at: datetime = Field(..., description="When this rate was recorded")
    base_currency: str = Field(default="USD", description="Base currency for this rate")
    rate_source: str = Field(default="simulated", description="Source of the rate data")


class RatesHistoryResponse(BaseModel):
    """Response model for historical exchange rates."""

    currency: str | None = Field(None, description="Specific currency (if filtered)")
    rates: list[HistoricalRateInfo] = Field(..., description="List of historical rates")
    period: dict[str, datetime] = Field(..., description="Time period covered")
    total_records: int = Field(..., description="Total number of records returned")
    base_currency: str = Field(default="USD", description="Base currency for all rates")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the history was retrieved",
    )
    metadata: dict[str, str] = Field(
        default_factory=lambda: {
            "rate_source": "simulated",
            "data_interval": "hourly",
        },
        description="Additional metadata about the historical data",
    )
