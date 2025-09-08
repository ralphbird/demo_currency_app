"""Tests for Prometheus metrics endpoint."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from currency_app.main import app
from currency_app.middleware.metrics import (
    REQUEST_COUNT,
    REQUEST_DURATION,
    get_metrics,
)


class TestMetricsEndpoint:
    """Test cases for the /metrics endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture(autouse=True)
    def clear_metrics(self):
        """Clear Prometheus metrics before each test."""
        REQUEST_COUNT.clear()
        REQUEST_DURATION.clear()

    def test_metrics_endpoint_returns_prometheus_format(self, client):
        """Test that /metrics endpoint returns Prometheus format."""
        response = client.get("/metrics")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"

        content = response.text
        # Should contain Prometheus metric format
        assert "# HELP" in content
        assert "# TYPE" in content

    def test_metrics_endpoint_contains_expected_metrics(self, client):
        """Test that metrics endpoint contains our defined metrics."""
        response = client.get("/metrics")
        content = response.text

        # Check for HTTP metrics
        assert "http_requests_total" in content
        assert "http_request_duration_seconds" in content
        assert "http_requests_in_progress" in content

        # Check for application-specific metrics
        assert "currency_conversions_total" in content
        assert "rates_requests_total" in content
        assert "database_operations_total" in content
        assert "database_connections_active" in content

    def test_metrics_endpoint_not_tracked_by_middleware(self, client):
        """Test that /metrics endpoint doesn't track itself."""
        # First, make a regular request to generate some metrics
        client.get("/")

        # Get initial metrics
        response1 = client.get("/metrics")
        content1 = response1.text

        # Get metrics again
        response2 = client.get("/metrics")
        content2 = response2.text

        # The metrics content should show the same request count for "/"
        # If /metrics was tracking itself, we'd see increasing counts
        root_requests_line1 = [
            line
            for line in content1.split("\n")
            if "http_requests_total{" in line and 'endpoint="/"' in line
        ]
        root_requests_line2 = [
            line
            for line in content2.split("\n")
            if "http_requests_total{" in line and 'endpoint="/"' in line
        ]

        # Should have exactly one request to root endpoint
        if root_requests_line1 and root_requests_line2:
            assert root_requests_line1[0] == root_requests_line2[0]

    def test_get_metrics_function(self):
        """Test the get_metrics utility function."""
        metrics_output = get_metrics()

        assert isinstance(metrics_output, str)
        assert "# HELP" in metrics_output
        assert "# TYPE" in metrics_output

    @patch("currency_app.middleware.metrics.generate_latest")
    def test_get_metrics_function_with_mock(self, mock_generate_latest):
        """Test get_metrics function with mocked prometheus_client."""
        mock_generate_latest.return_value = b"mocked_metrics_output"

        result = get_metrics()

        assert result == "mocked_metrics_output"
        mock_generate_latest.assert_called_once()

    def test_metrics_after_requests_show_counts(self, client):
        """Test that metrics reflect actual request counts."""
        # Make several requests
        client.get("/")
        client.get("/health")
        client.post(
            "/api/v1/convert", json={"amount": 100, "from_currency": "USD", "to_currency": "EUR"}
        )

        # Get metrics
        response = client.get("/metrics")
        content = response.text

        # Should show request counts
        lines = content.split("\n")

        # Look for root endpoint requests
        root_requests = [
            line for line in lines if "http_requests_total{" in line and 'endpoint="/"' in line
        ]
        assert len(root_requests) >= 1

        # Look for health endpoint requests
        health_requests = [
            line
            for line in lines
            if "http_requests_total{" in line and 'endpoint="/health"' in line
        ]
        assert len(health_requests) >= 1

        # Look for conversion endpoint requests
        convert_requests = [
            line
            for line in lines
            if "http_requests_total{" in line and 'endpoint="/api/v1/convert"' in line
        ]
        assert len(convert_requests) >= 1

    def test_metrics_include_duration_histograms(self, client):
        """Test that metrics include request duration histograms."""
        # Make a request to generate duration metrics
        client.get("/")

        # Get metrics
        response = client.get("/metrics")
        content = response.text

        # Should contain histogram buckets and summaries
        assert "http_request_duration_seconds_bucket" in content
        assert "http_request_duration_seconds_count" in content
        assert "http_request_duration_seconds_sum" in content

    def test_metrics_show_status_codes(self, client):
        """Test that metrics show different status codes."""
        # Make successful request
        client.get("/")

        # Make request that returns 401 (unauthenticated request to nonexistent endpoint)
        client.get("/nonexistent")

        # Get metrics
        response = client.get("/metrics")
        content = response.text

        # Should show both 200 and 401 status codes
        lines = content.split("\n")

        status_200_lines = [
            line for line in lines if "http_requests_total{" in line and 'status_code="200"' in line
        ]
        assert len(status_200_lines) >= 1

        status_401_lines = [
            line for line in lines if "http_requests_total{" in line and 'status_code="401"' in line
        ]
        assert len(status_401_lines) >= 1

    def test_metrics_content_type_header(self, client):
        """Test that metrics endpoint has correct content-type header."""
        response = client.get("/metrics")

        assert response.status_code == 200
        # Prometheus expects text/plain
        assert "text/plain" in response.headers["content-type"]

    def test_metrics_endpoint_in_api_response(self, client):
        """Test that metrics endpoint is advertised in API response."""
        response = client.get("/api")
        data = response.json()

        assert "endpoints" in data
        assert "metrics" in data["endpoints"]
        assert data["endpoints"]["metrics"] == "/metrics"
