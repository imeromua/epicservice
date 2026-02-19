"""Tests for rate limiting middleware."""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from middlewares.rate_limit import setup_rate_limiting, limiter
from middlewares.rate_limit_config import RateLimitConfig


@pytest.fixture
def app_with_rate_limit():
    """Create FastAPI app with rate limiting."""
    app = FastAPI()
    setup_rate_limiting(app)

    @app.get("/test")
    @limiter.limit("3/minute")
    async def test_endpoint(request: Request):
        return {"message": "success"}

    @app.get("/unlimited")
    async def unlimited_endpoint():
        return {"message": "no limit"}

    return app


def test_rate_limit_not_exceeded(app_with_rate_limit):
    """Test that requests within limit succeed."""
    client = TestClient(app_with_rate_limit)

    # First 3 requests should succeed
    for i in range(3):
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json()["message"] == "success"


def test_rate_limit_exceeded(app_with_rate_limit):
    """Test that exceeding limit returns 429."""
    client = TestClient(app_with_rate_limit)

    # First 3 requests succeed
    for i in range(3):
        client.get("/test")

    # 4th request should fail
    response = client.get("/test")
    assert response.status_code == 429
    assert response.json()["error"] == "RateLimitExceeded"


def test_rate_limit_headers(app_with_rate_limit):
    """Test that rate limit headers are present."""
    client = TestClient(app_with_rate_limit)

    response = client.get("/test")
    assert response.status_code == 200

    # Check headers
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers


def test_unlimited_endpoint(app_with_rate_limit):
    """Test that endpoints without limit work."""
    client = TestClient(app_with_rate_limit)

    # Should allow many requests
    for i in range(10):
        response = client.get("/unlimited")
        assert response.status_code == 200


def test_rate_limit_config():
    """Test RateLimitConfig class."""
    # Test basic limits
    assert RateLimitConfig.SEARCH == "10/minute"
    assert RateLimitConfig.ADMIN_BROADCAST == "1/minute"

    # Test admin multiplier
    admin_search = RateLimitConfig.get_limit("search", is_admin=True)
    assert admin_search == "30/minute"  # 10 * 3

    # Test get_all_limits
    all_limits = RateLimitConfig.get_all_limits()
    assert "SEARCH" in all_limits
    assert "ADMIN_BROADCAST" in all_limits
