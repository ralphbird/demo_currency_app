"""Tests for PrometheusMiddleware class."""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import Request, Response

from currency_app.middleware.metrics import (
    IN_PROGRESS_REQUESTS,
    REQUEST_COUNT,
    REQUEST_DURATION,
    PrometheusMiddleware,
)


class TestPrometheusMiddleware:
    """Test cases for PrometheusMiddleware."""

    @pytest.fixture(autouse=True)
    def clear_metrics(self):
        """Clear Prometheus metrics before each test."""
        REQUEST_COUNT.clear()
        REQUEST_DURATION.clear()
        IN_PROGRESS_REQUESTS.set(0)

    @pytest.fixture
    def middleware(self):
        """Create PrometheusMiddleware instance."""
        mock_app = Mock()
        return PrometheusMiddleware(mock_app)

    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock(spec=Request)
        request.method = "GET"
        request.url.path = "/api/v1/convert"
        request.scope = {"route": Mock(path="/api/v1/convert")}
        return request

    @pytest.fixture
    def mock_response(self):
        """Create mock response."""
        response = Mock(spec=Response)
        response.status_code = 200
        return response

    async def test_middleware_initialization(self, middleware):
        """Test middleware initialization."""
        assert isinstance(middleware, PrometheusMiddleware)
        assert hasattr(middleware, "app")

    async def test_dispatch_successful_request(self, middleware, mock_request, mock_response):
        """Test successful request processing."""
        # Mock call_next to return response
        call_next = AsyncMock(return_value=mock_response)

        # Execute middleware
        result = await middleware.dispatch(mock_request, call_next)

        # Verify response is returned
        assert result == mock_response

        # Verify call_next was called
        call_next.assert_called_once_with(mock_request)

        # Verify metrics were recorded (Counter creates both _total and _created samples)
        request_count_samples = next(iter(REQUEST_COUNT.collect())).samples
        total_samples = [s for s in request_count_samples if s.name.endswith("_total")]
        assert len(total_samples) == 1
        sample = total_samples[0]
        assert sample.labels["method"] == "GET"
        assert sample.labels["endpoint"] == "/api/v1/convert"
        assert sample.labels["status_code"] == "200"
        assert sample.value == 1.0

        # Verify duration was recorded
        duration_samples = next(iter(REQUEST_DURATION.collect())).samples
        assert len([s for s in duration_samples if s.name.endswith("_count")]) == 1

        # Verify in-progress requests is back to 0
        assert IN_PROGRESS_REQUESTS._value._value == 0

    async def test_dispatch_failed_request(self, middleware, mock_request):
        """Test failed request processing."""
        # Mock call_next to raise exception
        call_next = AsyncMock(side_effect=Exception("Test error"))

        # Execute middleware and expect exception
        with pytest.raises(Exception, match="Test error"):
            await middleware.dispatch(mock_request, call_next)

        # Verify error metrics were recorded (Counter creates both _total and _created samples)
        request_count_samples = next(iter(REQUEST_COUNT.collect())).samples
        total_samples = [s for s in request_count_samples if s.name.endswith("_total")]
        assert len(total_samples) == 1
        sample = total_samples[0]
        assert sample.labels["status_code"] == "500"
        assert sample.value == 1.0

        # Verify in-progress requests is decremented even on error
        assert IN_PROGRESS_REQUESTS._value._value == 0

    async def test_dispatch_skips_metrics_endpoint(self, middleware):
        """Test that /metrics endpoint is skipped."""
        # Create request for metrics endpoint
        request = Mock(spec=Request)
        request.url.path = "/metrics"

        mock_response = Mock(spec=Response)
        call_next = AsyncMock(return_value=mock_response)

        # Execute middleware
        result = await middleware.dispatch(request, call_next)

        # Verify response is returned without processing
        assert result == mock_response
        call_next.assert_called_once_with(request)

        # Verify no metrics were recorded (no _total samples should be present)
        request_count_samples = next(iter(REQUEST_COUNT.collect())).samples
        total_samples = [s for s in request_count_samples if s.name.endswith("_total")]
        assert len(total_samples) == 0

    async def test_dispatch_tracks_in_progress_requests(
        self, middleware, mock_request, mock_response
    ):
        """Test that in-progress requests are tracked correctly."""
        initial_value = IN_PROGRESS_REQUESTS._value._value

        # Mock call_next to check in-progress count during execution
        async def check_in_progress(request):
            # During request processing, count should be incremented
            assert IN_PROGRESS_REQUESTS._value._value == initial_value + 1
            return mock_response

        call_next = AsyncMock(side_effect=check_in_progress)

        # Execute middleware
        await middleware.dispatch(mock_request, call_next)

        # After completion, count should be back to initial
        assert IN_PROGRESS_REQUESTS._value._value == initial_value

    async def test_dispatch_records_duration(self, middleware, mock_request, mock_response):
        """Test that request duration is recorded correctly."""
        call_next = AsyncMock(return_value=mock_response)

        # Execute middleware
        await middleware.dispatch(mock_request, call_next)

        # Verify duration histogram was updated
        duration_samples = next(iter(REQUEST_DURATION.collect())).samples
        count_sample = next(s for s in duration_samples if s.name.endswith("_count"))
        assert count_sample.value == 1.0

        # Check that observe was called (histogram should have buckets)
        bucket_samples = [s for s in duration_samples if s.name.endswith("_bucket")]
        assert len(bucket_samples) > 0

        # Check that sum exists and is reasonable (should be > 0 for any real duration)
        sum_sample = next(s for s in duration_samples if s.name.endswith("_sum"))
        assert sum_sample.value >= 0

    def test_get_endpoint_pattern_with_route(self, middleware):
        """Test endpoint pattern extraction with FastAPI route."""
        request = Mock(spec=Request)
        request.scope = {"route": Mock(path="/api/v1/convert")}
        request.url.path = "/api/v1/convert"

        result = middleware._get_endpoint_pattern(request)
        assert result == "/api/v1/convert"

    def test_get_endpoint_pattern_without_route(self, middleware):
        """Test endpoint pattern extraction without FastAPI route."""
        request = Mock(spec=Request)
        request.scope = {}
        request.url.path = "/api/v1/convert"

        result = middleware._get_endpoint_pattern(request)
        assert result == "/api/v1/convert"

    def test_get_endpoint_pattern_normalizes_uuids(self, middleware):
        """Test that UUID patterns are normalized."""
        request = Mock(spec=Request)
        request.scope = {}
        request.url.path = "/api/v1/conversion/123e4567-e89b-12d3-a456-426614174000"

        result = middleware._get_endpoint_pattern(request)
        assert result == "/api/v1/conversion/{uuid}"

    def test_get_endpoint_pattern_normalizes_numeric_ids(self, middleware):
        """Test that numeric ID patterns are normalized."""
        request = Mock(spec=Request)
        request.scope = {}
        request.url.path = "/api/v1/user/12345/profile"

        result = middleware._get_endpoint_pattern(request)
        assert result == "/api/v1/user/{id}/profile"

    def test_get_endpoint_pattern_multiple_ids(self, middleware):
        """Test normalization with multiple ID patterns."""
        request = Mock(spec=Request)
        request.scope = {}
        request.url.path = "/api/v1/user/123/conversion/456e7890-a12b-34cd-e567-890123456789"

        result = middleware._get_endpoint_pattern(request)
        assert result == "/api/v1/user/{id}/conversion/{uuid}"
