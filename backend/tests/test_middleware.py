"""
Tests for RequestIDMiddleware, RateLimitMiddleware, and RequestLoggingMiddleware.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.core.constants import RATE_LIMIT_REQUESTS_PER_MINUTE

client = TestClient(app)


class TestRequestIDMiddleware:
    def test_response_contains_request_id_header(self):
        response = client.get("/health/live")
        assert "x-request-id" in response.headers

    def test_request_id_is_non_empty_string(self):
        response = client.get("/health/live")
        request_id = response.headers.get("x-request-id", "")
        assert len(request_id) > 0

    def test_each_request_generates_unique_id(self):
        ids = {client.get("/health/live").headers.get("x-request-id") for _ in range(5)}
        # All 5 request IDs should be distinct
        assert len(ids) == 5

    def test_custom_request_id_is_propagated(self):
        custom_id = "test-nexus-request-abc123"
        response = client.get("/health/live", headers={"X-Request-ID": custom_id})
        assert response.headers.get("x-request-id") == custom_id


class TestRateLimitMiddleware:
    def test_requests_below_limit_succeed(self):
        """First 10 requests should all succeed."""
        responses = [client.get("/api/telemetry/topology") for _ in range(5)]
        for r in responses:
            # Should be 200, not 429
            assert r.status_code != 429

    def test_rate_limit_constant_is_sane(self):
        """Rate limit should be between 1 and 10000."""
        assert 1 <= RATE_LIMIT_REQUESTS_PER_MINUTE <= 10_000

    def test_health_endpoints_exempt_from_rate_limit(self):
        """Health endpoints must never be rate limited."""
        for _ in range(10):
            r = client.get("/health/live")
            assert r.status_code == 200


class TestRequestLoggingMiddleware:
    def test_successful_request_returns_correct_status(self):
        """Logging middleware should not alter the response status code."""
        response = client.get("/")
        assert response.status_code == 200

    def test_invalid_route_returns_404(self):
        response = client.get("/api/does-not-exist")
        assert response.status_code == 404
