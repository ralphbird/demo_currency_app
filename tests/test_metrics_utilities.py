"""Tests for Prometheus metrics utility functions."""

import pytest

from currency_app.middleware.metrics import (
    CURRENCY_CONVERSIONS_TOTAL,
    DATABASE_OPERATIONS_TOTAL,
    RATES_REQUESTS_TOTAL,
    record_currency_conversion,
    record_database_operation,
    record_rates_request,
)


class TestMetricsUtilities:
    """Test cases for metrics utility functions."""

    @pytest.fixture(autouse=True)
    def clear_metrics(self):
        """Clear Prometheus metrics before each test."""
        CURRENCY_CONVERSIONS_TOTAL.clear()
        RATES_REQUESTS_TOTAL.clear()
        DATABASE_OPERATIONS_TOTAL.clear()

    def test_record_currency_conversion_success(self):
        """Test recording successful currency conversion."""
        record_currency_conversion("USD", "EUR", success=True)

        # Get metric samples (Counter creates both _total and _created samples)
        samples = next(iter(CURRENCY_CONVERSIONS_TOTAL.collect())).samples
        total_samples = [s for s in samples if s.name.endswith("_total")]
        assert len(total_samples) == 1

        sample = total_samples[0]
        assert sample.labels["from_currency"] == "USD"
        assert sample.labels["to_currency"] == "EUR"
        assert sample.labels["status"] == "success"
        assert sample.value == 1.0

    def test_record_currency_conversion_error(self):
        """Test recording failed currency conversion."""
        record_currency_conversion("USD", "EUR", success=False)

        # Get metric samples (Counter creates both _total and _created samples)
        samples = next(iter(CURRENCY_CONVERSIONS_TOTAL.collect())).samples
        total_samples = [s for s in samples if s.name.endswith("_total")]
        assert len(total_samples) == 1

        sample = total_samples[0]
        assert sample.labels["from_currency"] == "USD"
        assert sample.labels["to_currency"] == "EUR"
        assert sample.labels["status"] == "error"
        assert sample.value == 1.0

    def test_record_currency_conversion_default_success(self):
        """Test that record_currency_conversion defaults to success=True."""
        record_currency_conversion("GBP", "JPY")

        # Get metric samples (Counter creates both _total and _created samples)
        samples = next(iter(CURRENCY_CONVERSIONS_TOTAL.collect())).samples
        total_samples = [s for s in samples if s.name.endswith("_total")]
        assert len(total_samples) == 1

        sample = total_samples[0]
        assert sample.labels["status"] == "success"

    def test_record_currency_conversion_multiple_calls(self):
        """Test multiple currency conversion recordings."""
        record_currency_conversion("USD", "EUR", success=True)
        record_currency_conversion("USD", "EUR", success=True)
        record_currency_conversion("USD", "EUR", success=False)
        record_currency_conversion("GBP", "JPY", success=True)

        # Get metric samples (Counter creates both _total and _created samples)
        samples = next(iter(CURRENCY_CONVERSIONS_TOTAL.collect())).samples
        total_samples = [s for s in samples if s.name.endswith("_total")]
        assert len(total_samples) == 3  # Three unique label combinations

        # Find specific samples
        usd_eur_success = next(
            s
            for s in total_samples
            if s.labels["from_currency"] == "USD"
            and s.labels["to_currency"] == "EUR"
            and s.labels["status"] == "success"
        )
        assert usd_eur_success.value == 2.0

        usd_eur_error = next(
            s
            for s in total_samples
            if s.labels["from_currency"] == "USD"
            and s.labels["to_currency"] == "EUR"
            and s.labels["status"] == "error"
        )
        assert usd_eur_error.value == 1.0

        gbp_jpy_success = next(
            s
            for s in total_samples
            if s.labels["from_currency"] == "GBP"
            and s.labels["to_currency"] == "JPY"
            and s.labels["status"] == "success"
        )
        assert gbp_jpy_success.value == 1.0

    def test_record_rates_request_success(self):
        """Test recording successful rates request."""
        record_rates_request("current", success=True)

        # Get metric samples (Counter creates both _total and _created samples)
        samples = next(iter(RATES_REQUESTS_TOTAL.collect())).samples
        total_samples = [s for s in samples if s.name.endswith("_total")]
        assert len(total_samples) == 1

        sample = total_samples[0]
        assert sample.labels["endpoint"] == "current"
        assert sample.labels["status"] == "success"
        assert sample.value == 1.0

    def test_record_rates_request_error(self):
        """Test recording failed rates request."""
        record_rates_request("history", success=False)

        # Get metric samples (Counter creates both _total and _created samples)
        samples = next(iter(RATES_REQUESTS_TOTAL.collect())).samples
        total_samples = [s for s in samples if s.name.endswith("_total")]
        assert len(total_samples) == 1

        sample = total_samples[0]
        assert sample.labels["endpoint"] == "history"
        assert sample.labels["status"] == "error"
        assert sample.value == 1.0

    def test_record_rates_request_default_success(self):
        """Test that record_rates_request defaults to success=True."""
        record_rates_request("current")

        # Get metric samples (Counter creates both _total and _created samples)
        samples = next(iter(RATES_REQUESTS_TOTAL.collect())).samples
        total_samples = [s for s in samples if s.name.endswith("_total")]
        assert len(total_samples) == 1

        sample = total_samples[0]
        assert sample.labels["status"] == "success"

    def test_record_rates_request_multiple_endpoints(self):
        """Test recording requests to multiple endpoints."""
        record_rates_request("current", success=True)
        record_rates_request("current", success=True)
        record_rates_request("history", success=True)
        record_rates_request("current", success=False)

        # Get metric samples (Counter creates both _total and _created samples)
        samples = next(iter(RATES_REQUESTS_TOTAL.collect())).samples
        total_samples = [s for s in samples if s.name.endswith("_total")]
        assert len(total_samples) == 3  # Three unique label combinations

        # Check specific samples
        current_success = next(
            s
            for s in total_samples
            if s.labels["endpoint"] == "current" and s.labels["status"] == "success"
        )
        assert current_success.value == 2.0

        current_error = next(
            s
            for s in total_samples
            if s.labels["endpoint"] == "current" and s.labels["status"] == "error"
        )
        assert current_error.value == 1.0

        history_success = next(
            s
            for s in total_samples
            if s.labels["endpoint"] == "history" and s.labels["status"] == "success"
        )
        assert history_success.value == 1.0

    def test_record_database_operation_success(self):
        """Test recording successful database operation."""
        record_database_operation("SELECT", "conversions", success=True)

        # Get metric samples (Counter creates both _total and _created samples)
        samples = next(iter(DATABASE_OPERATIONS_TOTAL.collect())).samples
        total_samples = [s for s in samples if s.name.endswith("_total")]
        assert len(total_samples) == 1

        sample = total_samples[0]
        assert sample.labels["operation"] == "SELECT"
        assert sample.labels["table"] == "conversions"
        assert sample.labels["status"] == "success"
        assert sample.value == 1.0

    def test_record_database_operation_error(self):
        """Test recording failed database operation."""
        record_database_operation("INSERT", "rate_history", success=False)

        # Get metric samples (Counter creates both _total and _created samples)
        samples = next(iter(DATABASE_OPERATIONS_TOTAL.collect())).samples
        total_samples = [s for s in samples if s.name.endswith("_total")]
        assert len(total_samples) == 1

        sample = total_samples[0]
        assert sample.labels["operation"] == "INSERT"
        assert sample.labels["table"] == "rate_history"
        assert sample.labels["status"] == "error"
        assert sample.value == 1.0

    def test_record_database_operation_default_success(self):
        """Test that record_database_operation defaults to success=True."""
        record_database_operation("UPDATE", "users")

        # Get metric samples (Counter creates both _total and _created samples)
        samples = next(iter(DATABASE_OPERATIONS_TOTAL.collect())).samples
        total_samples = [s for s in samples if s.name.endswith("_total")]
        assert len(total_samples) == 1

        sample = total_samples[0]
        assert sample.labels["status"] == "success"

    def test_record_database_operation_multiple_operations(self):
        """Test recording multiple database operations."""
        record_database_operation("SELECT", "conversions", success=True)
        record_database_operation("SELECT", "conversions", success=True)
        record_database_operation("INSERT", "conversions", success=True)
        record_database_operation("SELECT", "rate_history", success=True)
        record_database_operation("SELECT", "conversions", success=False)

        # Get metric samples (Counter creates both _total and _created samples)
        samples = next(iter(DATABASE_OPERATIONS_TOTAL.collect())).samples
        total_samples = [s for s in samples if s.name.endswith("_total")]
        assert len(total_samples) == 4  # Four unique label combinations

        # Check specific samples
        select_conversions_success = next(
            s
            for s in total_samples
            if s.labels["operation"] == "SELECT"
            and s.labels["table"] == "conversions"
            and s.labels["status"] == "success"
        )
        assert select_conversions_success.value == 2.0

        insert_conversions_success = next(
            s
            for s in total_samples
            if s.labels["operation"] == "INSERT"
            and s.labels["table"] == "conversions"
            and s.labels["status"] == "success"
        )
        assert insert_conversions_success.value == 1.0

        select_history_success = next(
            s
            for s in total_samples
            if s.labels["operation"] == "SELECT"
            and s.labels["table"] == "rate_history"
            and s.labels["status"] == "success"
        )
        assert select_history_success.value == 1.0

        select_conversions_error = next(
            s
            for s in total_samples
            if s.labels["operation"] == "SELECT"
            and s.labels["table"] == "conversions"
            and s.labels["status"] == "error"
        )
        assert select_conversions_error.value == 1.0

    def test_all_utility_functions_together(self):
        """Test that all utility functions work together without interference."""
        # Record metrics from all utility functions
        record_currency_conversion("USD", "EUR")
        record_rates_request("current")
        record_database_operation("SELECT", "conversions")

        # Verify each metric has one total sample (Counter creates both _total and _created)
        conversion_samples = next(iter(CURRENCY_CONVERSIONS_TOTAL.collect())).samples
        conversion_total_samples = [s for s in conversion_samples if s.name.endswith("_total")]
        assert len(conversion_total_samples) == 1

        rates_samples = next(iter(RATES_REQUESTS_TOTAL.collect())).samples
        rates_total_samples = [s for s in rates_samples if s.name.endswith("_total")]
        assert len(rates_total_samples) == 1

        db_samples = next(iter(DATABASE_OPERATIONS_TOTAL.collect())).samples
        db_total_samples = [s for s in db_samples if s.name.endswith("_total")]
        assert len(db_total_samples) == 1

        # Verify labels are correct for each
        assert conversion_total_samples[0].labels["from_currency"] == "USD"
        assert rates_total_samples[0].labels["endpoint"] == "current"
        assert db_total_samples[0].labels["operation"] == "SELECT"
