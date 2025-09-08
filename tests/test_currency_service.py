"""Unit tests for currency service."""

from decimal import Decimal

import pytest

from currency_app.models.conversion import ConversionRequest
from currency_app.services.currency_service import CurrencyService, InvalidCurrencyError


class TestCurrencyService:
    """Test cases for CurrencyService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.currency_service = CurrencyService()

    def test_validate_currency_valid_lowercase(self):
        """Test currency validation with lowercase input."""
        result = self.currency_service.validate_currency("usd")
        assert result == "USD"

    def test_validate_currency_valid_uppercase(self):
        """Test currency validation with uppercase input."""
        result = self.currency_service.validate_currency("EUR")
        assert result == "EUR"

    def test_validate_currency_invalid(self):
        """Test currency validation with invalid currency."""
        with pytest.raises(InvalidCurrencyError) as exc_info:
            self.currency_service.validate_currency("INVALID")

        assert "INVALID" in str(exc_info.value)
        assert "not supported" in str(exc_info.value)

    def test_get_exchange_rate_same_currency(self):
        """Test exchange rate for same currency."""
        rate = self.currency_service.get_exchange_rate("USD", "USD")
        assert rate == Decimal("1.0000")

    def test_get_exchange_rate_usd_to_eur(self):
        """Test USD to EUR exchange rate."""
        rate = self.currency_service.get_exchange_rate("USD", "EUR")
        expected = Decimal("0.8523")
        assert rate == expected

    def test_get_exchange_rate_eur_to_usd(self):
        """Test EUR to USD exchange rate (inverse)."""
        rate = self.currency_service.get_exchange_rate("EUR", "USD")
        # Should be 1 / 0.8523 ≈ 1.173304
        assert rate > Decimal("1.17")
        assert rate < Decimal("1.18")

    def test_get_exchange_rate_cross_currency(self):
        """Test cross currency rate (EUR to GBP)."""
        rate = self.currency_service.get_exchange_rate("EUR", "GBP")
        # EUR rate = 0.8523, GBP rate = 0.7891
        # Cross rate = 0.7891 / 0.8523 ≈ 0.925872
        assert rate > Decimal("0.92")
        assert rate < Decimal("0.93")

    @pytest.mark.parametrize(
        "from_currency,to_currency",
        [
            ("INVALID", "USD"),
            ("USD", "INVALID"),
            ("INVALID", "INVALID"),
        ],
    )
    def test_get_exchange_rate_invalid_currencies(self, from_currency, to_currency):
        """Test exchange rate with invalid currencies."""
        with pytest.raises(InvalidCurrencyError):
            self.currency_service.get_exchange_rate(from_currency, to_currency)

    def test_convert_currency_basic(self):
        """Test basic currency conversion."""
        request = ConversionRequest(
            amount=Decimal("100.00"), from_currency="USD", to_currency="EUR"
        )

        response = self.currency_service.convert_currency(request)

        assert response.amount == Decimal("100.00")
        assert response.from_currency == "USD"
        assert response.to_currency == "EUR"
        assert response.exchange_rate == Decimal("0.852300")
        assert response.converted_amount == Decimal("85.23")
        assert response.request_id == request.request_id

    def test_convert_currency_same_currency(self):
        """Test conversion with same currency."""
        request = ConversionRequest(
            amount=Decimal("100.00"), from_currency="USD", to_currency="USD"
        )

        response = self.currency_service.convert_currency(request)

        assert response.converted_amount == Decimal("100.00")
        assert response.exchange_rate == Decimal("1.0000")

    def test_convert_currency_lowercase_input(self):
        """Test conversion with lowercase currency codes."""
        request = ConversionRequest(amount=Decimal("50.00"), from_currency="gbp", to_currency="jpy")

        response = self.currency_service.convert_currency(request)

        assert response.from_currency == "GBP"
        assert response.to_currency == "JPY"
        # GBP rate = 0.7891, JPY rate = 110.45
        # Cross rate = 110.45 / 0.7891 ≈ 139.98
        # 50 * 139.98 ≈ 6999
        assert response.converted_amount > Decimal("6990")
        assert response.converted_amount < Decimal("7010")

    def test_convert_currency_rounding(self):
        """Test proper rounding of conversion results."""
        request = ConversionRequest(amount=Decimal("33.33"), from_currency="USD", to_currency="EUR")

        response = self.currency_service.convert_currency(request)

        # 33.33 * 0.8523 = 28.411159, should round to 28.41
        assert response.converted_amount == Decimal("28.41")

    def test_get_supported_currencies(self):
        """Test getting supported currencies."""
        currencies = self.currency_service.get_supported_currencies()

        expected_currencies = ["AUD", "CAD", "CHF", "CNY", "EUR", "GBP", "JPY", "NZD", "SEK", "USD"]
        assert currencies == expected_currencies
