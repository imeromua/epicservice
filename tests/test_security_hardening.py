"""
Tests for abuse protection and HTTP security hardening.

Covers:
- OTP request rate limiting (per-IP and per-phone)
- Login endpoint rate limiting (per-IP)
- Refresh endpoint rate limiting (per-IP)
- Security headers (X-Content-Type-Options, Referrer-Policy)
- Cache-Control: no-store on auth token responses
- Graceful degradation when Redis is unavailable
- Normal flows still work under normal request rates
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_redis_mock(incr_sequence=None):
    """Return a MagicMock Redis client with configurable INCR responses."""
    mock_redis = MagicMock()
    if incr_sequence is not None:
        mock_redis.incr = AsyncMock(side_effect=incr_sequence)
    else:
        mock_redis.incr = AsyncMock(return_value=1)
    mock_redis.expire = AsyncMock(return_value=True)
    mock_redis.setex = AsyncMock()
    mock_redis.delete = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.exists = AsyncMock(return_value=0)
    return mock_redis


# ---------------------------------------------------------------------------
# Security headers tests
# ---------------------------------------------------------------------------

class TestSecurityHeaders:
    """HTTP responses must include safe security headers."""

    def test_health_endpoint_has_x_content_type_options(self):
        """X-Content-Type-Options: nosniff must be present on all responses."""
        from webapp.api import app

        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.headers.get("x-content-type-options") == "nosniff"

    def test_health_endpoint_has_referrer_policy(self):
        """Referrer-Policy must be present on all responses."""
        from webapp.api import app

        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    def test_auth_login_has_security_headers(self):
        """Security headers must be present on auth endpoint responses."""
        from webapp.api import app
        from webapp.routers.auth import hash_password

        pwd_hash = hash_password("testpass")
        mock_user = MagicMock()
        mock_user.id = 10000000100
        mock_user.login = "headertest"
        mock_user.first_name = "Test"
        mock_user.password_hash = pwd_hash
        mock_user.role = "user"
        mock_user.status = "active"

        with patch("webapp.routers.auth.orm_get_user_by_login", new_callable=AsyncMock, return_value=mock_user):
            client = TestClient(app)
            resp = client.post("/api/auth/login", json={"login": "headertest", "password": "testpass"})

        assert resp.status_code == 200
        assert resp.headers.get("x-content-type-options") == "nosniff"
        assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    def test_no_x_frame_options_for_tma_compatibility(self):
        """X-Frame-Options must NOT be set to preserve Telegram Mini App embedding."""
        from webapp.api import app

        client = TestClient(app)
        resp = client.get("/health")
        # Must not restrict framing — TMA needs iframe embedding via web.telegram.org
        assert "x-frame-options" not in resp.headers


# ---------------------------------------------------------------------------
# Cache-Control tests on token-issuing endpoints
# ---------------------------------------------------------------------------

class TestCacheControlOnAuthEndpoints:
    """Token-issuing auth endpoints must return Cache-Control: no-store."""

    def test_login_response_has_no_store(self):
        from webapp.api import app
        from webapp.routers.auth import hash_password

        pwd_hash = hash_password("pass123")
        mock_user = MagicMock()
        mock_user.id = 10000000200
        mock_user.login = "cachetest"
        mock_user.first_name = "Cache"
        mock_user.password_hash = pwd_hash
        mock_user.role = "user"
        mock_user.status = "active"

        with patch("webapp.routers.auth.orm_get_user_by_login", new_callable=AsyncMock, return_value=mock_user):
            client = TestClient(app)
            resp = client.post("/api/auth/login", json={"login": "cachetest", "password": "pass123"})

        assert resp.status_code == 200
        assert "no-store" in resp.headers.get("cache-control", "")

    def test_refresh_response_has_no_store(self):
        from webapp.api import app
        from webapp.routers.auth import create_token

        mock_user = MagicMock()
        mock_user.id = 10000000201
        mock_user.role = "user"
        mock_user.status = "active"

        refresh_token = create_token(10000000201, "refreshcache", "user", "refresh")

        with patch("webapp.routers.auth.orm_get_user_by_id", new_callable=AsyncMock, return_value=mock_user):
            client = TestClient(app)
            resp = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})

        assert resp.status_code == 200
        assert "no-store" in resp.headers.get("cache-control", "")

    def test_register_response_has_no_store(self):
        from webapp.api import app

        mock_user = MagicMock()
        mock_user.id = 10000000202
        mock_user.login = "regcache"
        mock_user.first_name = "RegCache"
        mock_user.role = "user"
        mock_user.status = "pending"

        with (
            patch("webapp.routers.auth.orm_get_user_by_login", new_callable=AsyncMock, return_value=None),
            patch("webapp.routers.auth.orm_get_user_by_id", new_callable=AsyncMock, return_value=None),
            patch("webapp.routers.auth.orm_create_standalone_user", new_callable=AsyncMock, return_value=mock_user),
        ):
            client = TestClient(app)
            resp = client.post("/api/auth/register", json={
                "login": "regcache",
                "password": "securepass",
                "first_name": "RegCache",
            })

        assert resp.status_code == 200
        assert "no-store" in resp.headers.get("cache-control", "")

    def test_phone_verify_response_has_no_store(self):
        from webapp.api import app

        mock_redis = _make_redis_mock(incr_sequence=[1, 1])

        mock_user = MagicMock()
        mock_user.id = 10000000203
        mock_user.login = None
        mock_user.first_name = "OTPCache"
        mock_user.role = "user"
        mock_user.status = "active"

        original_redis = getattr(__import__("webapp.api", fromlist=["app"]).app.state, "redis", None)
        from webapp.api import app as _app
        _app.state.redis = mock_redis
        try:
            with (
                patch("webapp.routers.auth.verify_otp", new_callable=AsyncMock, return_value=True),
                patch("webapp.routers.auth.orm_get_user_by_phone", new_callable=AsyncMock, return_value=mock_user),
            ):
                client = TestClient(_app)
                resp = client.post("/api/auth/phone/verify", json={
                    "phone": "+380991234567",
                    "otp": "123456",
                })
        finally:
            _app.state.redis = original_redis

        assert resp.status_code == 200
        assert "no-store" in resp.headers.get("cache-control", "")


# ---------------------------------------------------------------------------
# CORS header: X-Telegram-Init-Data must be in allowed headers
# ---------------------------------------------------------------------------

class TestCORSHeaders:
    """CORS configuration must expose X-Telegram-Init-Data for TMA flows."""

    def test_cors_allows_x_telegram_init_data_header(self):
        """OPTIONS preflight for a TMA-using cross-origin request must allow the header."""
        from webapp.api import app

        client = TestClient(app)
        resp = client.options(
            "/api/auth/login",
            headers={
                "Origin": "https://anubis-ua.pp.ua",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "X-Telegram-Init-Data",
            },
        )
        # The response should indicate the header is allowed
        allowed = resp.headers.get("access-control-allow-headers", "").lower()
        assert "x-telegram-init-data" in allowed


# ---------------------------------------------------------------------------
# Login rate limiting tests
# ---------------------------------------------------------------------------

class TestLoginRateLimit:
    """Login endpoint must reject requests exceeding the per-IP limit."""

    def test_login_rate_limit_triggers_429(self):
        """Exceeding the IP limit on /login returns 429."""
        from webapp.api import app

        # Simulate counter already over limit
        mock_redis = _make_redis_mock(incr_sequence=[11])

        original_redis = getattr(app.state, "redis", None)
        app.state.redis = mock_redis
        try:
            client = TestClient(app)
            resp = client.post("/api/auth/login", json={"login": "x", "password": "y"})
        finally:
            app.state.redis = original_redis

        assert resp.status_code == 429

    def test_login_within_limit_proceeds(self):
        """Requests within the IP limit pass through to normal auth logic."""
        from webapp.api import app
        from webapp.routers.auth import hash_password

        pwd_hash = hash_password("mypass")
        mock_user = MagicMock()
        mock_user.id = 10000000300
        mock_user.login = "ratelimitok"
        mock_user.first_name = "RL"
        mock_user.password_hash = pwd_hash
        mock_user.role = "user"
        mock_user.status = "active"

        # Counter within limit
        mock_redis = _make_redis_mock(incr_sequence=[1])

        original_redis = getattr(app.state, "redis", None)
        app.state.redis = mock_redis
        try:
            with patch("webapp.routers.auth.orm_get_user_by_login", new_callable=AsyncMock, return_value=mock_user):
                client = TestClient(app)
                resp = client.post("/api/auth/login", json={"login": "ratelimitok", "password": "mypass"})
        finally:
            app.state.redis = original_redis

        assert resp.status_code == 200

    def test_login_no_redis_does_not_block(self):
        """Login without Redis (graceful degradation) must not block requests."""
        from webapp.api import app
        from webapp.routers.auth import hash_password

        pwd_hash = hash_password("pass")
        mock_user = MagicMock()
        mock_user.id = 10000000301
        mock_user.login = "noredislogin"
        mock_user.first_name = "NoRedis"
        mock_user.password_hash = pwd_hash
        mock_user.role = "user"
        mock_user.status = "active"

        original_redis = getattr(app.state, "redis", None)
        app.state.redis = None  # Redis unavailable
        try:
            with patch("webapp.routers.auth.orm_get_user_by_login", new_callable=AsyncMock, return_value=mock_user):
                client = TestClient(app)
                resp = client.post("/api/auth/login", json={"login": "noredislogin", "password": "pass"})
        finally:
            app.state.redis = original_redis

        # Without Redis, rate limiting degrades safely — request proceeds
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Refresh rate limiting tests
# ---------------------------------------------------------------------------

class TestRefreshRateLimit:
    """Refresh endpoint must reject requests exceeding the per-IP limit."""

    def test_refresh_rate_limit_triggers_429(self):
        """Exceeding the IP limit on /refresh returns 429."""
        from webapp.api import app
        from webapp.routers.auth import create_token

        mock_redis = _make_redis_mock(incr_sequence=[31])

        refresh_token = create_token(10000000400, "refreshrl", "user", "refresh")

        original_redis = getattr(app.state, "redis", None)
        app.state.redis = mock_redis
        try:
            client = TestClient(app)
            resp = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
        finally:
            app.state.redis = original_redis

        assert resp.status_code == 429

    def test_refresh_no_redis_does_not_block(self):
        """Refresh without Redis must still work (graceful degradation)."""
        from webapp.api import app
        from webapp.routers.auth import create_token

        mock_user = MagicMock()
        mock_user.id = 10000000401
        mock_user.role = "user"
        mock_user.status = "active"

        refresh_token = create_token(10000000401, "noredisrefresh", "user", "refresh")

        original_redis = getattr(app.state, "redis", None)
        app.state.redis = None
        try:
            with patch("webapp.routers.auth.orm_get_user_by_id", new_callable=AsyncMock, return_value=mock_user):
                client = TestClient(app)
                resp = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
        finally:
            app.state.redis = original_redis

        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# OTP request rate limiting tests
# ---------------------------------------------------------------------------

class TestOTPRequestRateLimit:
    """OTP request endpoint must enforce per-IP and per-phone rate limits."""

    def _make_otp_redis(self, ip_count=1, phone_count=1):
        """Return a Redis mock whose INCR returns ip_count then phone_count."""
        mock_redis = _make_redis_mock(incr_sequence=[ip_count, phone_count])
        mock_redis.setex = AsyncMock()
        mock_redis.delete = AsyncMock()
        return mock_redis

    def test_otp_request_ip_rate_limit_triggers_429(self):
        """Exceeding the per-IP OTP request limit returns 429."""
        from webapp.api import app

        # IP counter is over limit (6 > 5)
        mock_redis = _make_redis_mock(incr_sequence=[6])

        original_redis = getattr(app.state, "redis", None)
        app.state.redis = mock_redis
        try:
            client = TestClient(app)
            resp = client.post("/api/auth/phone/request", json={"phone": "+380991234567"})
        finally:
            app.state.redis = original_redis

        assert resp.status_code == 429

    def test_otp_request_phone_rate_limit_triggers_429(self):
        """Exceeding the per-phone OTP request limit returns 429."""
        from webapp.api import app

        # IP counter is within limit, phone counter is over limit (4 > 3)
        mock_redis = _make_redis_mock(incr_sequence=[1, 4])

        original_redis = getattr(app.state, "redis", None)
        app.state.redis = mock_redis
        try:
            with patch("webapp.routers.auth.orm_get_user_by_phone", new_callable=AsyncMock, return_value=None):
                client = TestClient(app)
                resp = client.post("/api/auth/phone/request", json={"phone": "+380991234567"})
        finally:
            app.state.redis = original_redis

        assert resp.status_code == 429

    def test_otp_request_within_limits_succeeds(self):
        """OTP request within both limits succeeds normally."""
        from webapp.api import app

        mock_redis = _make_redis_mock(incr_sequence=[1, 1])
        mock_redis.setex = AsyncMock()
        mock_redis.delete = AsyncMock()

        original_redis = getattr(app.state, "redis", None)
        app.state.redis = mock_redis
        try:
            with patch("webapp.routers.auth.orm_get_user_by_phone", new_callable=AsyncMock, return_value=None):
                client = TestClient(app)
                resp = client.post("/api/auth/phone/request", json={"phone": "+380991234567"})
        finally:
            app.state.redis = original_redis

        assert resp.status_code == 200

    def test_otp_request_no_redis_returns_503(self):
        """OTP request without Redis still returns 503 (Redis required for OTP storage)."""
        from webapp.api import app

        original_redis = getattr(app.state, "redis", None)
        app.state.redis = None
        try:
            client = TestClient(app)
            resp = client.post("/api/auth/phone/request", json={"phone": "+380991234567"})
        finally:
            app.state.redis = original_redis

        # OTP endpoint requires Redis for OTP storage — 503 is correct behavior
        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# Rate limiter unit tests
# ---------------------------------------------------------------------------

class TestRateLimiterUnit:
    """Unit tests for webapp.utils.rate_limit.is_rate_limited."""

    @pytest.mark.asyncio
    async def test_allows_within_limit(self):
        from webapp.utils.rate_limit import is_rate_limited

        mock_redis = MagicMock()
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock()

        result = await is_rate_limited(mock_redis, "test_scope", "127.0.0.1", 5, 60)
        assert result is False

    @pytest.mark.asyncio
    async def test_blocks_over_limit(self):
        from webapp.utils.rate_limit import is_rate_limited

        mock_redis = MagicMock()
        mock_redis.incr = AsyncMock(return_value=6)
        mock_redis.expire = AsyncMock()

        result = await is_rate_limited(mock_redis, "test_scope", "127.0.0.1", 5, 60)
        assert result is True

    @pytest.mark.asyncio
    async def test_at_exact_limit_is_allowed(self):
        from webapp.utils.rate_limit import is_rate_limited

        mock_redis = MagicMock()
        mock_redis.incr = AsyncMock(return_value=5)
        mock_redis.expire = AsyncMock()

        result = await is_rate_limited(mock_redis, "test_scope", "127.0.0.1", 5, 60)
        assert result is False

    @pytest.mark.asyncio
    async def test_graceful_degradation_with_none_redis(self):
        from webapp.utils.rate_limit import is_rate_limited

        # Redis is None — must return False (allow) without raising
        result = await is_rate_limited(None, "test_scope", "127.0.0.1", 5, 60)
        assert result is False

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_redis_error(self):
        from webapp.utils.rate_limit import is_rate_limited

        mock_redis = MagicMock()
        mock_redis.incr = AsyncMock(side_effect=Exception("Redis connection lost"))

        # Redis error — must return False (fail open) without raising
        result = await is_rate_limited(mock_redis, "test_scope", "127.0.0.1", 5, 60)
        assert result is False

    @pytest.mark.asyncio
    async def test_expire_set_on_first_request(self):
        """TTL must be set only when counter goes from 0→1."""
        from webapp.utils.rate_limit import is_rate_limited

        mock_redis = MagicMock()
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock()

        await is_rate_limited(mock_redis, "test_scope", "127.0.0.1", 5, 120)

        mock_redis.expire.assert_awaited_once()
        call_args = mock_redis.expire.call_args[0]
        assert call_args[1] == 120

    @pytest.mark.asyncio
    async def test_expire_not_set_on_subsequent_requests(self):
        """TTL must NOT be reset when counter is already > 1."""
        from webapp.utils.rate_limit import is_rate_limited

        mock_redis = MagicMock()
        mock_redis.incr = AsyncMock(return_value=3)
        mock_redis.expire = AsyncMock()

        await is_rate_limited(mock_redis, "test_scope", "127.0.0.1", 5, 60)

        mock_redis.expire.assert_not_awaited()


# ---------------------------------------------------------------------------
# Production config validation tests
# ---------------------------------------------------------------------------

class TestProductionConfigValidation:
    """_validate_production_config() emits warnings for security-sensitive misconfig."""

    def test_warns_when_webapp_url_is_default(self, monkeypatch, caplog):
        """A warning is emitted when WEBAPP_URL is still the placeholder default."""
        import logging

        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("WEBAPP_URL", "https://epicservice.example.com")
        monkeypatch.setenv("REDIS_ENABLED", "true")
        monkeypatch.setenv("ADMIN_IDS", "12345")
        monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.1")

        import importlib
        import sys
        # Remove cached config module so env changes take effect
        for mod in list(sys.modules.keys()):
            if mod == "config":
                del sys.modules[mod]

        with caplog.at_level(logging.WARNING, logger="config"):
            import config as cfg  # noqa: F401

        assert any("WEBAPP_URL" in r.message for r in caplog.records if r.levelno >= logging.WARNING)

    def test_warns_when_redis_disabled_in_production(self, monkeypatch, caplog):
        """A warning is emitted when Redis is disabled in production."""
        import logging

        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("WEBAPP_URL", "https://real.example.com")
        monkeypatch.setenv("REDIS_ENABLED", "false")
        monkeypatch.setenv("ADMIN_IDS", "12345")
        monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.1")

        import sys
        for mod in list(sys.modules.keys()):
            if mod == "config":
                del sys.modules[mod]

        with caplog.at_level(logging.WARNING, logger="config"):
            import config as cfg  # noqa: F401

        assert any("REDIS_ENABLED" in r.message for r in caplog.records if r.levelno >= logging.WARNING)

    def test_warns_when_admin_ids_empty_in_production(self, monkeypatch, caplog):
        """A warning is emitted when ADMIN_IDS is empty in production."""
        import logging

        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("WEBAPP_URL", "https://real.example.com")
        monkeypatch.setenv("REDIS_ENABLED", "true")
        monkeypatch.setenv("ADMIN_IDS", "")
        monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.1")

        import sys
        for mod in list(sys.modules.keys()):
            if mod == "config":
                del sys.modules[mod]

        with caplog.at_level(logging.WARNING, logger="config"):
            import config as cfg  # noqa: F401

        assert any("ADMIN_IDS" in r.message for r in caplog.records if r.levelno >= logging.WARNING)

    def test_warns_when_trusted_proxies_not_set_in_production(self, monkeypatch, caplog):
        """A warning is emitted when TRUSTED_PROXIES is unset in production."""
        import logging

        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("WEBAPP_URL", "https://real.example.com")
        monkeypatch.setenv("REDIS_ENABLED", "true")
        monkeypatch.setenv("ADMIN_IDS", "12345")
        monkeypatch.delenv("TRUSTED_PROXIES", raising=False)

        import sys
        for mod in list(sys.modules.keys()):
            if mod == "config":
                del sys.modules[mod]

        with caplog.at_level(logging.WARNING, logger="config"):
            import config as cfg  # noqa: F401

        assert any("TRUSTED_PROXIES" in r.message for r in caplog.records if r.levelno >= logging.WARNING)

    def test_no_production_warnings_when_config_is_correct(self, monkeypatch, caplog):
        """No [production config] warnings when all settings are properly configured."""
        import logging

        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("WEBAPP_URL", "https://real.example.com")
        monkeypatch.setenv("REDIS_ENABLED", "true")
        monkeypatch.setenv("ADMIN_IDS", "12345")
        monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.1")

        import sys
        for mod in list(sys.modules.keys()):
            if mod == "config":
                del sys.modules[mod]

        with caplog.at_level(logging.WARNING, logger="config"):
            import config as cfg  # noqa: F401

        prod_warnings = [
            r for r in caplog.records
            if r.levelno >= logging.WARNING and "[production config]" in r.message
        ]
        assert prod_warnings == []

    def test_no_production_guardrails_in_development(self, monkeypatch, caplog):
        """_validate_production_config is not called in development mode."""
        import logging

        monkeypatch.setenv("APP_ENV", "development")
        monkeypatch.delenv("TRUSTED_PROXIES", raising=False)
        monkeypatch.setenv("REDIS_ENABLED", "false")

        import sys
        for mod in list(sys.modules.keys()):
            if mod == "config":
                del sys.modules[mod]

        with caplog.at_level(logging.WARNING, logger="config"):
            import config as cfg  # noqa: F401

        prod_warnings = [
            r for r in caplog.records
            if r.levelno >= logging.WARNING and "[production config]" in r.message
        ]
        assert prod_warnings == []
