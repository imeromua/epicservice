"""Tests for the download token system (TMA file download fix).

Tests cover:
- webapp.utils.download_tokens: token creation, validation, consumption, expiry
- POST /api/download-token  endpoint (user)
- POST /api/admin/download-token endpoint (admin / moderator)
- GET  /api/admin/export/stock with dl_token
"""
import hashlib
import hmac as _hmac
import json
import time
import urllib.parse
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tma_init_data(user_id: int, bot_token: str = "123456:TESTTOKEN") -> str:
    user_data = {"id": user_id, "first_name": f"User{user_id}"}
    params = {
        "user": json.dumps(user_data, separators=(",", ":")),
        "auth_date": str(int(time.time())),
        "query_id": "test",
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = _hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    hash_val = _hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    params["hash"] = hash_val
    return urllib.parse.urlencode(params)


def _make_mock_user(role="user"):
    u = MagicMock()
    u.role = role
    return u


# ---------------------------------------------------------------------------
# Unit tests: webapp.utils.download_tokens
# ---------------------------------------------------------------------------

class TestDownloadTokens:
    def test_create_and_consume(self):
        from webapp.utils.download_tokens import create_download_token, validate_and_consume_token
        token = create_download_token(123, "/api/archives/download-all/123", role="user")
        assert isinstance(token, str) and len(token) > 20

        data = validate_and_consume_token(token, "/api/archives/download-all/123")
        assert data["user_id"] == 123
        assert data["role"] == "user"

    def test_one_time_use(self):
        from fastapi import HTTPException
        from webapp.utils.download_tokens import create_download_token, validate_and_consume_token
        token = create_download_token(1, "/api/archive/download/file.xlsx", role="user")
        # First call should succeed
        validate_and_consume_token(token, "/api/archive/download/file.xlsx")
        # Second call should raise 401
        with pytest.raises(HTTPException) as exc_info:
            validate_and_consume_token(token, "/api/archive/download/file.xlsx")
        assert exc_info.value.status_code == 401

    def test_resource_url_mismatch(self):
        from fastapi import HTTPException
        from webapp.utils.download_tokens import create_download_token, validate_and_consume_token
        token = create_download_token(1, "/api/archives/download-all/1", role="user")
        with pytest.raises(HTTPException) as exc_info:
            validate_and_consume_token(token, "/api/archives/download-all/999")
        assert exc_info.value.status_code == 401

    def test_expired_token(self):
        """Token with past expiry should raise 401."""
        import webapp.utils.download_tokens as dt
        from fastapi import HTTPException
        token = dt.create_download_token(1, "/api/archive/download/x.xlsx", role="user")
        # Manually backdate expiry
        with dt._lock:
            dt._tokens[token]["expires_at"] = time.time() - 1

        with pytest.raises(HTTPException) as exc_info:
            dt.validate_and_consume_token(token, "/api/archive/download/x.xlsx")
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# Integration tests: POST /api/download-token (user endpoint)
# ---------------------------------------------------------------------------

class TestUserDownloadTokenEndpoint:
    def test_returns_token_for_valid_user(self):
        from webapp.api import app
        user_id = 555
        init_data = _make_tma_init_data(user_id=user_id)

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/download-token",
            json={"resource_url": f"/api/archives/download-all/{user_id}"},
            headers={"X-Telegram-Init-Data": init_data},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "token" in body
        assert body["expires_in"] == 60

    def test_rejects_invalid_resource_url(self):
        from webapp.api import app
        user_id = 555
        init_data = _make_tma_init_data(user_id=user_id)

        client = TestClient(app, raise_server_exceptions=False)
        # Wrong user_id in URL
        resp = client.post(
            "/api/download-token",
            json={"resource_url": "/api/archives/download-all/999"},
            headers={"X-Telegram-Init-Data": init_data},
        )
        assert resp.status_code == 400

    def test_rejects_admin_url(self):
        """Users cannot obtain tokens for admin endpoints."""
        from webapp.api import app
        user_id = 555
        init_data = _make_tma_init_data(user_id=user_id)

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/download-token",
            json={"resource_url": "/api/admin/export/stock"},
            headers={"X-Telegram-Init-Data": init_data},
        )
        assert resp.status_code == 400

    def test_requires_tma_auth(self):
        from webapp.api import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/download-token",
            json={"resource_url": "/api/archives/download-all/1"},
        )
        assert resp.status_code in (401, 422)


# ---------------------------------------------------------------------------
# Integration tests: POST /api/admin/download-token
# ---------------------------------------------------------------------------

class TestAdminDownloadTokenEndpoint:
    def test_returns_token_for_admin(self):
        from webapp.api import app
        admin_id = 777
        init_data = _make_tma_init_data(user_id=admin_id)

        with patch("webapp.deps.ADMIN_IDS", [admin_id]), \
             patch("webapp.routers.admin.ADMIN_IDS", [admin_id]):
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post(
                "/api/admin/download-token",
                json={"resource_url": "/api/admin/export/stock"},
                headers={"X-Telegram-Init-Data": init_data},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "token" in body
        assert body["expires_in"] == 60

    def test_returns_token_for_moderator(self):
        from webapp.api import app
        mod_id = 888
        init_data = _make_tma_init_data(user_id=mod_id)
        mock_user = _make_mock_user("moderator")

        with patch("webapp.deps.ADMIN_IDS", []), \
             patch("webapp.routers.admin.ADMIN_IDS", []), \
             patch("webapp.deps.orm_get_user_by_id", new_callable=AsyncMock, return_value=mock_user):
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post(
                "/api/admin/download-token",
                json={"resource_url": "/api/admin/export/stock"},
                headers={"X-Telegram-Init-Data": init_data},
            )

        assert resp.status_code == 200

    def test_denied_for_regular_user(self):
        from webapp.api import app
        user_id = 111
        init_data = _make_tma_init_data(user_id=user_id)

        with patch("webapp.deps.ADMIN_IDS", []), \
             patch("webapp.routers.admin.ADMIN_IDS", []), \
             patch("webapp.deps.orm_get_user_by_id", new_callable=AsyncMock, return_value=_make_mock_user("user")):
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post(
                "/api/admin/download-token",
                json={"resource_url": "/api/admin/export/stock"},
                headers={"X-Telegram-Init-Data": init_data},
            )

        assert resp.status_code == 403

    def test_rejects_non_admin_url(self):
        from webapp.api import app
        admin_id = 777
        init_data = _make_tma_init_data(user_id=admin_id)

        with patch("webapp.deps.ADMIN_IDS", [admin_id]), \
             patch("webapp.routers.admin.ADMIN_IDS", [admin_id]):
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post(
                "/api/admin/download-token",
                json={"resource_url": "/api/archives/download-all/123"},
                headers={"X-Telegram-Init-Data": init_data},
            )

        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Integration tests: GET /api/admin/export/stock with dl_token
# ---------------------------------------------------------------------------

class TestExportStockWithDlToken:
    def test_export_denied_without_auth(self):
        from webapp.api import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/admin/export/stock")
        assert resp.status_code == 401

    def test_export_allowed_with_valid_admin_token(self):
        from webapp.api import app
        from webapp.utils.download_tokens import create_download_token
        token = create_download_token(777, "/api/admin/export/stock", role="admin")

        with patch("webapp.routers.admin._create_stock_report_sync", return_value=None):
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get(f"/api/admin/export/stock?dl_token={token}")

        # 500 because report_path is None (mocked), but NOT 401/403
        assert resp.status_code != 401
        assert resp.status_code != 403

    def test_export_denied_with_user_token(self):
        from webapp.api import app
        from webapp.utils.download_tokens import create_download_token
        # Token with 'user' role should be denied
        token = create_download_token(123, "/api/admin/export/stock", role="user")

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get(f"/api/admin/export/stock?dl_token={token}")

        assert resp.status_code == 403

    def test_export_denied_with_wrong_resource_token(self):
        from webapp.api import app
        from webapp.utils.download_tokens import create_download_token
        # Token for a different URL
        token = create_download_token(777, "/api/admin/archives/download-all", role="admin")

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get(f"/api/admin/export/stock?dl_token={token}")

        assert resp.status_code == 401

    def test_export_tma_auth_still_works(self):
        """Existing TMA header auth must still work for backward compat."""
        from webapp.api import app
        admin_id = 333
        init_data = _make_tma_init_data(user_id=admin_id)

        with patch("webapp.deps.ADMIN_IDS", [admin_id]), \
             patch("webapp.routers.admin.ADMIN_IDS", [admin_id]), \
             patch("webapp.routers.admin._create_stock_report_sync", return_value=None):
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get(
                "/api/admin/export/stock",
                headers={"X-Telegram-Init-Data": init_data},
            )

        assert resp.status_code != 403
