"""Tests for RatesHistoryService."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from currency_app.models.database import RateHistory
from currency_app.services.rates_history_service import RatesHistoryService


class TestRatesHistoryService:
    """Test cases for RatesHistoryService."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def rates_history_service(self, mock_db_session):
        """Create a RatesHistoryService instance with mocked dependencies."""
        return RatesHistoryService(mock_db_session)

    @pytest.fixture
    def sample_rate_history_records(self):
        """Create sample RateHistory records for testing."""
        base_time = datetime.now(UTC)
        records = []

        for i in range(5):
            record = Mock(spec=RateHistory)
            record.currency = "EUR"
            record.rate = Decimal("0.85") + Decimal(str(i * 0.01))  # 0.85, 0.86, 0.87, 0.88, 0.89
            record.recorded_at = base_time - timedelta(hours=i)
            record.base_currency = "USD"
            record.rate_source = "simulated"
            records.append(record)

        return records

    def test_init(self, mock_db_session):
        """Test RatesHistoryService initialization."""
        service = RatesHistoryService(mock_db_session)

        assert service.db_session == mock_db_session
        assert hasattr(service, "currency_service")

    def test_store_current_rates(self, rates_history_service, mock_db_session):
        """Test storing current rates as historical snapshot."""
        # Mock the currency service to return rates
        mock_rates_response = Mock()
        mock_rate_info = Mock()
        mock_rate_info.currency = "EUR"
        mock_rate_info.rate = Decimal("0.85")
        mock_rates_response.rates = [mock_rate_info]

        # Create a mock for the currency service and its method
        rates_history_service.currency_service = Mock()
        rates_history_service.currency_service.get_current_rates.return_value = mock_rates_response

        # Execute
        result = rates_history_service.store_current_rates()

        # Verify
        assert result == 1
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

        # Check the RateHistory object was created correctly
        added_record = mock_db_session.add.call_args[0][0]
        assert added_record.currency == "EUR"
        assert added_record.rate == Decimal("0.85")
        assert added_record.base_currency == "USD"
        assert added_record.rate_source == "simulated"

    @patch("currency_app.services.rates_history_service.random.normalvariate")
    def test_generate_historical_data_for_demo(
        self, mock_random, rates_history_service, mock_db_session
    ):
        """Test generating demo historical data."""
        # Mock random to return consistent values
        mock_random.return_value = 0.01  # 1% variation

        # Mock the currency service exchange rates
        rates_history_service.currency_service.EXCHANGE_RATES = {
            "USD": Decimal("1.0000"),
            "EUR": Decimal("0.8500"),
        }

        # Execute - generate 2 days of data
        result = rates_history_service.generate_historical_data_for_demo(days_back=2)

        # Verify
        expected_records = 2 * 4 * 2  # 2 days * 4 snapshots per day * 2 currencies
        assert result == expected_records

        # Should have called add for each record
        assert mock_db_session.add.call_count == expected_records
        mock_db_session.commit.assert_called_once()

        # Verify USD rates are always 1.0
        added_records = [call[0][0] for call in mock_db_session.add.call_args_list]
        usd_records = [r for r in added_records if r.currency == "USD"]
        for usd_record in usd_records:
            assert usd_record.rate == Decimal("1.000000")

        # Verify EUR rates have variation
        eur_records = [r for r in added_records if r.currency == "EUR"]
        for eur_record in eur_records:
            assert eur_record.rate != Decimal("0.8500")  # Should be varied

    def test_get_rates_history_basic(
        self, rates_history_service, mock_db_session, sample_rate_history_records
    ):
        """Test basic historical rates retrieval."""
        # Setup mock query chain
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = sample_rate_history_records
        mock_db_session.query.return_value = mock_query

        # Execute
        result = rates_history_service.get_rates_history()

        # Verify
        assert result.currency is None  # No currency filter
        assert len(result.rates) == 5
        assert result.total_records == 5
        assert result.base_currency == "USD"

        # Check the rates are properly converted
        assert result.rates[0].currency == "EUR"
        assert result.rates[0].rate == Decimal("0.85")

    def test_get_rates_history_with_currency_filter(
        self, rates_history_service, mock_db_session, sample_rate_history_records
    ):
        """Test historical rates retrieval with currency filter."""
        # Setup mock query chain
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = sample_rate_history_records
        mock_db_session.query.return_value = mock_query

        # Execute with currency filter
        result = rates_history_service.get_rates_history(currency="EUR", days=7, limit=10)

        # Verify currency filter was applied
        assert result.currency == "EUR"

        # Verify query was built correctly
        assert mock_query.filter.call_count >= 2  # Time range + currency filter
        mock_query.order_by.assert_called_once()
        mock_query.limit.assert_called_once_with(10)

    def test_get_rates_history_empty_results(self, rates_history_service, mock_db_session):
        """Test historical rates retrieval with no data."""
        # Setup mock query chain to return empty results
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_db_session.query.return_value = mock_query

        # Execute
        result = rates_history_service.get_rates_history()

        # Verify
        assert len(result.rates) == 0
        assert result.total_records == 0
        assert "start" in result.period
        assert "end" in result.period

    def test_get_currency_history_for_chart(
        self, rates_history_service, sample_rate_history_records
    ):
        """Test getting currency history formatted for charting."""
        # Mock get_rates_history to return sample data
        mock_response = Mock()
        mock_response.rates = []

        for record in sample_rate_history_records:
            rate_info = Mock()
            rate_info.recorded_at = record.recorded_at
            rate_info.rate = record.rate
            rate_info.currency = record.currency
            mock_response.rates.append(rate_info)

        rates_history_service.get_rates_history = Mock(return_value=mock_response)

        # Execute
        result = rates_history_service.get_currency_history_for_chart("EUR", days=7)

        # Verify
        assert len(result) == 5
        assert all("timestamp" in item for item in result)
        assert all("rate" in item for item in result)
        assert all("currency" in item for item in result)
        assert all(item["currency"] == "EUR" for item in result)

    def test_get_rate_statistics(self, rates_history_service):
        """Test getting rate statistics for a currency."""
        # Create mock response with sample data
        mock_response = Mock()
        mock_response.rates = []

        # Create sample rates: 1.0, 1.1, 0.9, 1.05, 0.95 (oldest to newest in desc order)
        rates_values = [
            Decimal("1.0"),
            Decimal("1.1"),
            Decimal("0.9"),
            Decimal("1.05"),
            Decimal("0.95"),
        ]
        for rate in rates_values:
            rate_info = Mock()
            rate_info.rate = rate
            mock_response.rates.append(rate_info)

        rates_history_service.get_rates_history = Mock(return_value=mock_response)

        # Execute
        result = rates_history_service.get_rate_statistics("EUR", days=30)

        # Verify
        assert result["current_rate"] == 1.0  # First in desc order
        assert result["min_rate"] == 0.9
        assert result["max_rate"] == 1.1
        assert result["avg_rate"] == 1.0  # (1.0 + 1.1 + 0.9 + 1.05 + 0.95) / 5
        assert result["total_records"] == 5
        assert "change_percent" in result
        assert "volatility" in result

    def test_get_rate_statistics_empty_data(self, rates_history_service):
        """Test getting rate statistics with no data."""
        # Mock empty response
        mock_response = Mock()
        mock_response.rates = []
        rates_history_service.get_rates_history = Mock(return_value=mock_response)

        # Execute
        result = rates_history_service.get_rate_statistics("EUR", days=30)

        # Verify default values
        assert result["current_rate"] == 0.0
        assert result["min_rate"] == 0.0
        assert result["max_rate"] == 0.0
        assert result["avg_rate"] == 0.0
        assert result["total_records"] == 0
        assert result["change_percent"] == 0.0
        assert result["volatility"] == 0.0

    def test_get_rate_statistics_single_record(self, rates_history_service):
        """Test getting rate statistics with single record."""
        # Mock response with single record
        mock_response = Mock()
        rate_info = Mock()
        rate_info.rate = Decimal("1.0")
        mock_response.rates = [rate_info]

        rates_history_service.get_rates_history = Mock(return_value=mock_response)

        # Execute
        result = rates_history_service.get_rate_statistics("EUR", days=30)

        # Verify
        assert result["current_rate"] == 1.0
        assert result["min_rate"] == 1.0
        assert result["max_rate"] == 1.0
        assert result["avg_rate"] == 1.0
        assert result["total_records"] == 1
        assert result["volatility"] == 0.0  # No variance with single record
