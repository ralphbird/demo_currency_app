"""Tests for Pydantic models."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import uuid_utils.compat as uuid

from currency_app.models.conversion import (
    ErrorResponse,
    HistoricalRateInfo,
    RatesHistoryResponse,
)


class TestErrorResponse:
    """Test ErrorResponse model and its create method."""

    def test_error_response_create_minimal(self):
        """Test ErrorResponse.create() with minimal parameters."""
        error_response = ErrorResponse.create(code="TEST_ERROR", message="Test error message")

        assert error_response.error["code"] == "TEST_ERROR"
        assert error_response.error["message"] == "Test error message"
        assert "timestamp" in error_response.error
        assert isinstance(error_response.error["timestamp"], str)  # Now ISO string
        assert "details" not in error_response.error
        assert "request_id" not in error_response.error

    def test_error_response_create_with_details(self):
        """Test ErrorResponse.create() with details parameter."""
        details = {"field": "amount", "issue": "must be positive"}

        error_response = ErrorResponse.create(
            code="VALIDATION_ERROR", message="Validation failed", details=details
        )

        assert error_response.error["code"] == "VALIDATION_ERROR"
        assert error_response.error["message"] == "Validation failed"
        assert error_response.error["details"] == details
        assert "request_id" not in error_response.error

    def test_error_response_create_with_request_id(self):
        """Test ErrorResponse.create() with request_id parameter."""
        request_id = uuid.uuid7()

        error_response = ErrorResponse.create(
            code="SERVER_ERROR", message="Internal server error", request_id=request_id
        )

        assert error_response.error["code"] == "SERVER_ERROR"
        assert error_response.error["message"] == "Internal server error"
        assert error_response.error["request_id"] == str(request_id)
        assert "details" not in error_response.error

    def test_error_response_create_with_all_parameters(self):
        """Test ErrorResponse.create() with all optional parameters."""
        details = {"currency": "INVALID", "supported": "USD,EUR,GBP"}
        request_id = uuid.uuid7()

        error_response = ErrorResponse.create(
            code="INVALID_CURRENCY",
            message="Currency not supported",
            details=details,
            request_id=request_id,
        )

        assert error_response.error["code"] == "INVALID_CURRENCY"
        assert error_response.error["message"] == "Currency not supported"
        assert error_response.error["details"] == details
        assert error_response.error["request_id"] == str(request_id)
        assert "timestamp" in error_response.error
        assert isinstance(error_response.error["timestamp"], str)  # Now ISO string

    def test_error_response_create_with_none_details(self):
        """Test ErrorResponse.create() with explicit None details (should be omitted)."""
        error_response = ErrorResponse.create(
            code="TEST_ERROR", message="Test message", details=None
        )

        assert "details" not in error_response.error
        assert error_response.error["code"] == "TEST_ERROR"
        assert error_response.error["message"] == "Test message"

    def test_error_response_create_with_none_request_id(self):
        """Test ErrorResponse.create() with explicit None request_id (should be omitted)."""
        error_response = ErrorResponse.create(
            code="TEST_ERROR", message="Test message", request_id=None
        )

        assert "request_id" not in error_response.error
        assert error_response.error["code"] == "TEST_ERROR"
        assert error_response.error["message"] == "Test message"

    def test_error_response_create_timestamp_accuracy(self):
        """Test that timestamp is recent and properly formatted."""
        before = datetime.now(UTC)
        error_response = ErrorResponse.create(code="TEST", message="Test")
        after = datetime.now(UTC)

        timestamp_value = error_response.error["timestamp"]
        # Parse the ISO timestamp back to datetime for comparison
        if isinstance(timestamp_value, str):
            timestamp = datetime.fromisoformat(timestamp_value.replace("Z", "+00:00"))
            assert before <= timestamp <= after


class TestHistoricalRateInfo:
    """Test HistoricalRateInfo model."""

    def test_historical_rate_info_creation(self):
        """Test creating a HistoricalRateInfo instance."""
        recorded_at = datetime.now(UTC)

        rate_info = HistoricalRateInfo(
            currency="EUR",
            rate=Decimal("0.8500"),
            recorded_at=recorded_at,
            base_currency="USD",
            rate_source="simulated",
        )

        assert rate_info.currency == "EUR"
        assert rate_info.rate == Decimal("0.8500")
        assert rate_info.recorded_at == recorded_at
        assert rate_info.base_currency == "USD"
        assert rate_info.rate_source == "simulated"

    def test_historical_rate_info_defaults(self):
        """Test HistoricalRateInfo with default values."""
        recorded_at = datetime.now(UTC)

        rate_info = HistoricalRateInfo(
            currency="EUR", rate=Decimal("0.8500"), recorded_at=recorded_at
        )

        assert rate_info.base_currency == "USD"  # Default value
        assert rate_info.rate_source == "simulated"  # Default value

    def test_historical_rate_info_validation(self):
        """Test HistoricalRateInfo field validation."""
        import pytest
        from pydantic import ValidationError

        # Test missing required fields
        with pytest.raises(ValidationError):
            HistoricalRateInfo()  # type: ignore

        # Test invalid rate type
        with pytest.raises(ValidationError):
            HistoricalRateInfo(currency="EUR", rate="not_a_decimal", recorded_at=datetime.now(UTC))  # type: ignore


class TestRatesHistoryResponse:
    """Test RatesHistoryResponse model."""

    def test_rates_history_response_creation(self):
        """Test creating a RatesHistoryResponse instance."""
        start_time = datetime.now(UTC) - timedelta(days=7)
        end_time = datetime.now(UTC)

        rate_info = HistoricalRateInfo(
            currency="EUR", rate=Decimal("0.8500"), recorded_at=datetime.now(UTC)
        )

        response = RatesHistoryResponse(
            currency="EUR",
            rates=[rate_info],
            period={"start": start_time, "end": end_time},
            total_records=1,
        )

        assert response.currency == "EUR"
        assert len(response.rates) == 1
        assert response.rates[0] == rate_info
        assert response.period["start"] == start_time
        assert response.period["end"] == end_time
        assert response.total_records == 1
        assert response.base_currency == "USD"  # Default

    def test_rates_history_response_no_currency_filter(self):
        """Test RatesHistoryResponse without currency filter."""
        start_time = datetime.now(UTC) - timedelta(days=7)
        end_time = datetime.now(UTC)

        eur_rate = HistoricalRateInfo(
            currency="EUR", rate=Decimal("0.8500"), recorded_at=datetime.now(UTC)
        )

        gbp_rate = HistoricalRateInfo(
            currency="GBP", rate=Decimal("0.7800"), recorded_at=datetime.now(UTC)
        )

        response = RatesHistoryResponse(
            currency=None,
            rates=[eur_rate, gbp_rate],
            period={"start": start_time, "end": end_time},
            total_records=2,
        )

        assert response.currency is None  # No currency filter
        assert len(response.rates) == 2
        assert response.total_records == 2

    def test_rates_history_response_defaults(self):
        """Test RatesHistoryResponse with default values."""
        from datetime import timedelta

        start_time = datetime.now(UTC) - timedelta(days=1)
        end_time = datetime.now(UTC)

        response = RatesHistoryResponse(
            currency=None, rates=[], period={"start": start_time, "end": end_time}, total_records=0
        )

        assert response.base_currency == "USD"
        assert "rate_source" in response.metadata
        assert "data_interval" in response.metadata
        assert response.metadata["rate_source"] == "simulated"
        assert response.metadata["data_interval"] == "hourly"
        assert isinstance(response.timestamp, datetime)

    def test_rates_history_response_validation(self):
        """Test RatesHistoryResponse field validation."""
        import pytest
        from pydantic import ValidationError

        # Test missing required fields
        with pytest.raises(ValidationError):
            RatesHistoryResponse()  # type: ignore

        # Test invalid total_records type
        with pytest.raises(ValidationError):
            RatesHistoryResponse(
                currency=None,
                rates=[],
                period={"start": datetime.now(UTC), "end": datetime.now(UTC)},
                total_records="not_an_integer",  # type: ignore
            )
