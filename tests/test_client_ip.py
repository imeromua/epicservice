"""
Tests for proxy-aware client IP extraction (webapp/utils/client_ip.py).

Covers:
- No trusted proxies (default): always uses request.client.host
- Trusted proxy configured: uses X-Forwarded-For left-most entry
- Untrusted connecting IP: ignores X-Forwarded-For (spoofing protection)
- Trusted proxy with no XFF header: falls back to connecting IP
- Malformed XFF entry from trusted proxy: falls back to connecting IP
- CIDR notation in TRUSTED_PROXIES
- Unknown/missing client
"""

import os
from unittest.mock import MagicMock

import pytest


def _make_request(client_host: str = "1.2.3.4", xff: str = None) -> MagicMock:
    """Build a minimal mock Request object."""
    req = MagicMock()
    req.client = MagicMock()
    req.client.host = client_host
    headers = {}
    if xff is not None:
        headers["X-Forwarded-For"] = xff
    req.headers = headers
    return req


def _make_request_no_client(xff: str = None) -> MagicMock:
    """Build a mock Request with no client (e.g. Unix socket / test client)."""
    req = MagicMock()
    req.client = None
    headers = {}
    if xff is not None:
        headers["X-Forwarded-For"] = xff
    req.headers = headers
    return req


# ---------------------------------------------------------------------------
# Helpers to reset and configure the module-level cache between tests
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_trusted_proxy_cache():
    """Reset the module-level trusted proxy cache before each test."""
    from webapp.utils.client_ip import _reset_trusted_proxies_cache
    _reset_trusted_proxies_cache()
    yield
    _reset_trusted_proxies_cache()


# ---------------------------------------------------------------------------
# No trusted proxies configured (safe default)
# ---------------------------------------------------------------------------

class TestNoTrustedProxies:
    """When TRUSTED_PROXIES is not set, X-Forwarded-For is always ignored."""

    def test_uses_connecting_ip_without_xff(self, monkeypatch):
        monkeypatch.delenv("TRUSTED_PROXIES", raising=False)
        from webapp.utils.client_ip import get_client_ip

        req = _make_request("1.2.3.4")
        assert get_client_ip(req) == "1.2.3.4"

    def test_ignores_xff_when_no_trusted_proxies(self, monkeypatch):
        """XFF must be ignored when TRUSTED_PROXIES is not configured."""
        monkeypatch.delenv("TRUSTED_PROXIES", raising=False)
        from webapp.utils.client_ip import get_client_ip

        req = _make_request("1.2.3.4", xff="10.0.0.1")
        # Even though XFF says 10.0.0.1, the connecting IP is used because no proxies are trusted
        assert get_client_ip(req) == "1.2.3.4"

    def test_unknown_when_no_client(self, monkeypatch):
        monkeypatch.delenv("TRUSTED_PROXIES", raising=False)
        from webapp.utils.client_ip import get_client_ip

        req = _make_request_no_client()
        assert get_client_ip(req) == "unknown"


# ---------------------------------------------------------------------------
# Trusted proxy configured — should parse X-Forwarded-For
# ---------------------------------------------------------------------------

class TestTrustedProxy:
    """When the connecting IP is a trusted proxy, XFF is parsed and trusted."""

    def test_trusted_proxy_uses_xff_client(self, monkeypatch):
        """Connecting from a trusted proxy: use left-most XFF entry."""
        monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.1")
        from webapp.utils.client_ip import get_client_ip

        req = _make_request("10.0.0.1", xff="203.0.113.5")
        assert get_client_ip(req) == "203.0.113.5"

    def test_trusted_proxy_uses_leftmost_xff(self, monkeypatch):
        """With multiple XFF entries, the left-most (original client) is used."""
        monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.1")
        from webapp.utils.client_ip import get_client_ip

        req = _make_request("10.0.0.1", xff="203.0.113.5, 10.0.0.2, 10.0.0.1")
        assert get_client_ip(req) == "203.0.113.5"

    def test_trusted_proxy_no_xff_falls_back(self, monkeypatch):
        """Trusted proxy with no XFF header: fall back to the connecting IP."""
        monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.1")
        from webapp.utils.client_ip import get_client_ip

        req = _make_request("10.0.0.1")  # no XFF
        assert get_client_ip(req) == "10.0.0.1"

    def test_trusted_proxy_malformed_xff_falls_back(self, monkeypatch):
        """Malformed XFF entry from trusted proxy: fall back to connecting IP."""
        monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.1")
        from webapp.utils.client_ip import get_client_ip

        req = _make_request("10.0.0.1", xff="not-an-ip")
        assert get_client_ip(req) == "10.0.0.1"

    def test_trusted_proxy_cidr_range(self, monkeypatch):
        """Connecting IP within a trusted CIDR range: parse XFF."""
        monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.0/8")
        from webapp.utils.client_ip import get_client_ip

        req = _make_request("10.5.6.7", xff="203.0.113.99")
        assert get_client_ip(req) == "203.0.113.99"

    def test_multiple_trusted_proxies(self, monkeypatch):
        """Multiple trusted proxy entries (comma-separated)."""
        monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.1,192.168.1.1")
        from webapp.utils.client_ip import get_client_ip

        req = _make_request("192.168.1.1", xff="203.0.113.42")
        assert get_client_ip(req) == "203.0.113.42"

    def test_xff_whitespace_stripped(self, monkeypatch):
        """Whitespace around XFF IP entries is stripped correctly."""
        monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.1")
        from webapp.utils.client_ip import get_client_ip

        req = _make_request("10.0.0.1", xff="  203.0.113.7  , 10.0.0.1")
        assert get_client_ip(req) == "203.0.113.7"


# ---------------------------------------------------------------------------
# Spoofing protection: untrusted connecting IP ignores XFF
# ---------------------------------------------------------------------------

class TestSpoofingProtection:
    """X-Forwarded-For from untrusted sources must always be ignored."""

    def test_spoofed_xff_from_untrusted_source_ignored(self, monkeypatch):
        """An attacker sending XFF from an untrusted IP must not bypass rate limiting."""
        monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.1")
        from webapp.utils.client_ip import get_client_ip

        # Attacker connects directly (not via trusted proxy) with spoofed XFF
        req = _make_request("5.6.7.8", xff="127.0.0.1")
        # The spoofed XFF is ignored; the real connecting IP is returned
        assert get_client_ip(req) == "5.6.7.8"

    def test_untrusted_connecting_ip_bypasses_xff_regardless_of_xff_content(self, monkeypatch):
        monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.1")
        from webapp.utils.client_ip import get_client_ip

        req = _make_request("203.0.113.1", xff="192.168.0.1")
        assert get_client_ip(req) == "203.0.113.1"


# ---------------------------------------------------------------------------
# Invalid TRUSTED_PROXIES entries (should be logged and skipped)
# ---------------------------------------------------------------------------

class TestInvalidTrustedProxiesConfig:
    """Invalid TRUSTED_PROXIES entries should be skipped without crashing."""

    def test_invalid_entry_skipped(self, monkeypatch):
        """An invalid TRUSTED_PROXIES entry is skipped; valid entries still work."""
        monkeypatch.setenv("TRUSTED_PROXIES", "not-an-ip,10.0.0.1")
        from webapp.utils.client_ip import get_client_ip

        req = _make_request("10.0.0.1", xff="203.0.113.5")
        # Valid proxy 10.0.0.1 is still trusted despite invalid entry
        assert get_client_ip(req) == "203.0.113.5"

    def test_all_invalid_entries_means_no_trusted_proxies(self, monkeypatch):
        monkeypatch.setenv("TRUSTED_PROXIES", "bad-entry,also-bad")
        from webapp.utils.client_ip import get_client_ip

        req = _make_request("1.2.3.4", xff="10.0.0.1")
        assert get_client_ip(req) == "1.2.3.4"


# ---------------------------------------------------------------------------
# Integration: rate-limited endpoints use the centralized helper
# ---------------------------------------------------------------------------

class TestAuthRouterUsesClientIpHelper:
    """auth.py _get_client_ip must delegate to the centralized get_client_ip utility."""

    def test_auth_get_client_ip_delegates_to_utility(self, monkeypatch):
        """_get_client_ip in auth.py should call get_client_ip from client_ip.py."""
        monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.1")
        # Reset the cache so the new env var is picked up
        from webapp.utils.client_ip import _reset_trusted_proxies_cache
        _reset_trusted_proxies_cache()

        from webapp.routers.auth import _get_client_ip

        req = _make_request("10.0.0.1", xff="203.0.113.55")
        result = _get_client_ip(req)
        assert result == "203.0.113.55"
