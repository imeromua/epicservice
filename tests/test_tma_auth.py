"""
Tests for Telegram Mini App (TMA) authentication layer.

Covers:
- Valid vs invalid Telegram initData (HMAC validation)
- Client TMA routes: cannot access another user's resources (IDOR prevention)
- Admin TMA routes: reject missing/invalid initData and non-admin identities
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
    """
    Generate a valid Telegram initData string for a given user_id and bot_token.

    This follows the exact algorithm from Telegram docs:
      secret_key = HMAC-SHA256(key=b"WebAppData", data=bot_token)
      data_check_string = sorted key=value lines (excluding 'hash')
      hash = HMAC-SHA256(key=secret_key, data=data_check_string)
    """
    user_data = {"id": user_id, "first_name": f"User{user_id}", "username": f"user{user_id}"}
    params = {
        "user": json.dumps(user_data, separators=(",", ":")),
        "auth_date": str(int(time.time())),
        "query_id": "test_query_id",
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = _hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    hash_val = _hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    params["hash"] = hash_val
    return urllib.parse.urlencode(params)


def _make_expired_tma_init_data(user_id: int, bot_token: str = "123456:TESTTOKEN") -> str:
    """Generate initData with an auth_date far in the past (expired)."""
    user_data = {"id": user_id, "first_name": f"User{user_id}"}
    params = {
        "user": json.dumps(user_data, separators=(",", ":")),
        "auth_date": str(int(time.time()) - 200_000),  # > 24 hours ago
        "query_id": "test_expired",
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = _hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    hash_val = _hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    params["hash"] = hash_val
    return urllib.parse.urlencode(params)


def _make_jwt_token(user_id: int, role: str = "user") -> str:
    """Generate a JWT Bearer token for the standalone auth flow."""
    from webapp.routers.auth import create_token
    return create_token(user_id, f"user_{user_id}", role, "access")


def _make_mock_user(user_id: int = 1, role: str = "user", status: str = "active"):
    u = MagicMock()
    u.id = user_id
    u.role = role
    u.status = status
    return u


# ---------------------------------------------------------------------------
# _validate_tma_init_data unit tests
# ---------------------------------------------------------------------------

class TestValidateTmaInitData:
    """Unit tests for the core HMAC validation function in webapp/deps.py."""

    def test_valid_init_data_returns_user_id(self):
        from webapp.deps import _validate_tma_init_data

        init_data = _make_tma_init_data(user_id=42)
        assert _validate_tma_init_data(init_data) == 42

    def test_tampered_hash_raises_401(self):
        from fastapi import HTTPException
        from webapp.deps import _validate_tma_init_data

        init_data = _make_tma_init_data(user_id=42)
        # Tamper by appending a character to the hash parameter
        params = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        params["hash"] = params["hash"][:-1] + ("a" if params["hash"][-1] != "a" else "b")
        tampered = urllib.parse.urlencode(params)

        with pytest.raises(HTTPException) as exc_info:
            _validate_tma_init_data(tampered)
        assert exc_info.value.status_code == 401

    def test_missing_hash_raises_401(self):
        from fastapi import HTTPException
        from webapp.deps import _validate_tma_init_data

        # Build valid data but omit the 'hash' field
        user_data = {"id": 99}
        params = {
            "user": json.dumps(user_data),
            "auth_date": str(int(time.time())),
        }
        init_data = urllib.parse.urlencode(params)

        with pytest.raises(HTTPException) as exc_info:
            _validate_tma_init_data(init_data)
        assert exc_info.value.status_code == 401

    def test_expired_init_data_raises_401(self):
        from fastapi import HTTPException
        from webapp.deps import _validate_tma_init_data

        expired_data = _make_expired_tma_init_data(user_id=10)
        with pytest.raises(HTTPException) as exc_info:
            _validate_tma_init_data(expired_data)
        assert exc_info.value.status_code == 401

    def test_wrong_bot_token_raises_401(self):
        from fastapi import HTTPException
        from webapp.deps import _validate_tma_init_data

        # Signed with a different bot token than the one in config
        init_data = _make_tma_init_data(user_id=7, bot_token="999999:WRONGTOKEN")
        with pytest.raises(HTTPException) as exc_info:
            _validate_tma_init_data(init_data)
        assert exc_info.value.status_code == 401

    def test_empty_string_raises_401(self):
        from fastapi import HTTPException
        from webapp.deps import _validate_tma_init_data

        with pytest.raises(HTTPException) as exc_info:
            _validate_tma_init_data("")
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# Admin TMA routes — authentication enforcement
# ---------------------------------------------------------------------------

class TestAdminTmaAuth:
    """Admin endpoints must reject requests without valid TMA initData."""

    ADMIN_ENDPOINTS_GET = [
        "/api/admin/statistics",
        "/api/admin/users",
        "/api/admin/users/active",
        "/api/admin/users/all",
        "/api/admin/archives",
        "/api/admin/products/info",
        "/api/admin/reserved/by-department",
        "/api/admin/summary",
    ]

    def test_get_endpoints_reject_missing_header(self):
        from webapp.api import app
        client = TestClient(app)
        for endpoint in self.ADMIN_ENDPOINTS_GET:
            resp = client.get(endpoint)
            assert resp.status_code in (401, 422), (
                f"Expected 401/422 without TMA header, got {resp.status_code} for {endpoint}"
            )

    def test_get_endpoints_reject_invalid_init_data(self):
        from webapp.api import app
        client = TestClient(app)
        for endpoint in self.ADMIN_ENDPOINTS_GET:
            resp = client.get(endpoint, headers={"X-Telegram-Init-Data": "fake=data&hash=badhash"})
            assert resp.status_code == 401, (
                f"Expected 401 for invalid initData, got {resp.status_code} for {endpoint}"
            )

    def test_get_endpoints_reject_non_admin_user(self):
        from webapp.api import app
        non_admin_id = 999_999
        init_data = _make_tma_init_data(user_id=non_admin_id)
        client = TestClient(app)
        with patch("webapp.deps.ADMIN_IDS", []):
            for endpoint in self.ADMIN_ENDPOINTS_GET:
                resp = client.get(endpoint, headers={"X-Telegram-Init-Data": init_data})
                assert resp.status_code == 403, (
                    f"Expected 403 for non-admin, got {resp.status_code} for {endpoint}"
                )

    def test_import_rejects_missing_header(self):
        from webapp.api import app
        client = TestClient(app)
        import io
        dummy_file = io.BytesIO(b"fake xlsx")
        resp = client.post(
            "/api/admin/import",
            files={"file": ("test.xlsx", dummy_file, "application/octet-stream")},
        )
        assert resp.status_code in (401, 422)

    def test_import_rejects_invalid_init_data(self):
        from webapp.api import app
        client = TestClient(app)
        import io
        dummy_file = io.BytesIO(b"fake xlsx")
        resp = client.post(
            "/api/admin/import",
            files={"file": ("test.xlsx", dummy_file, "application/octet-stream")},
            headers={"X-Telegram-Init-Data": "fake=data&hash=badhash"},
        )
        assert resp.status_code == 401

    def test_danger_reset_moderation_rejects_missing_header(self):
        from webapp.api import app
        client = TestClient(app)
        resp = client.post("/api/admin/danger/reset-moderation")
        assert resp.status_code in (401, 422)

    def test_danger_reset_moderation_rejects_non_admin(self):
        from webapp.api import app
        init_data = _make_tma_init_data(user_id=555)
        client = TestClient(app)
        with patch("webapp.deps.ADMIN_IDS", []):
            resp = client.post(
                "/api/admin/danger/reset-moderation",
                headers={"X-Telegram-Init-Data": init_data},
            )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Danger zone: combined JWT + TMA auth (backward compat with existing tests)
# ---------------------------------------------------------------------------

class TestDangerZoneAnyAuth:
    """Danger zone endpoints accept JWT (backward compat) OR TMA initData."""

    DANGER_ENDPOINTS = [
        "/api/admin/danger/clear-database",
        "/api/admin/danger/delete-all-photos",
        "/api/admin/danger/delete-all-archives",
        "/api/admin/danger/full-wipe",
    ]

    def test_danger_endpoints_reject_missing_auth(self):
        from webapp.api import app
        client = TestClient(app)
        for endpoint in self.DANGER_ENDPOINTS:
            resp = client.post(endpoint)
            assert resp.status_code in (401, 422), (
                f"Expected 401/422 without any auth, got {resp.status_code} for {endpoint}"
            )

    def test_danger_endpoints_reject_invalid_jwt(self):
        from webapp.api import app
        client = TestClient(app)
        for endpoint in self.DANGER_ENDPOINTS:
            resp = client.post(endpoint, headers={"Authorization": "Bearer not-a-real-token"})
            assert resp.status_code == 401, (
                f"Expected 401 for bad JWT, got {resp.status_code} for {endpoint}"
            )

    def test_danger_endpoints_reject_non_admin_jwt(self):
        from webapp.api import app
        token = _make_jwt_token(user_id=999, role="user")
        client = TestClient(app)
        with patch("webapp.deps.ADMIN_IDS", []):
            for endpoint in self.DANGER_ENDPOINTS:
                resp = client.post(endpoint, headers={"Authorization": f"Bearer {token}"})
                assert resp.status_code == 403, (
                    f"Expected 403 for non-admin JWT, got {resp.status_code} for {endpoint}"
                )

    def test_danger_endpoints_reject_non_admin_tma(self):
        from webapp.api import app
        init_data = _make_tma_init_data(user_id=888)
        client = TestClient(app)
        with patch("webapp.deps.ADMIN_IDS", []):
            for endpoint in self.DANGER_ENDPOINTS:
                resp = client.post(endpoint, headers={"X-Telegram-Init-Data": init_data})
                assert resp.status_code == 403, (
                    f"Expected 403 for non-admin TMA, got {resp.status_code} for {endpoint}"
                )

    def test_danger_endpoints_reject_invalid_tma(self):
        from webapp.api import app
        client = TestClient(app)
        for endpoint in self.DANGER_ENDPOINTS:
            resp = client.post(
                endpoint, headers={"X-Telegram-Init-Data": "fake=data&hash=badhash"}
            )
            assert resp.status_code == 401, (
                f"Expected 401 for invalid TMA, got {resp.status_code} for {endpoint}"
            )


# ---------------------------------------------------------------------------
# Client TMA routes — IDOR prevention
# ---------------------------------------------------------------------------

class TestClientTmaIdroPrevention:
    """
    Client endpoints must use TMA-verified identity, not client-supplied user_id.

    An attacker who sends requests with a different user_id in the URL path or
    request body must only affect their own data (the TMA identity).
    """

    def _tma_headers(self, user_id: int) -> dict:
        return {"X-Telegram-Init-Data": _make_tma_init_data(user_id=user_id)}

    def test_list_endpoint_requires_tma_header(self):
        """GET /list/{any_id} without TMA header should fail."""
        from webapp.api import app
        client = TestClient(app)
        resp = client.get("/api/list/12345")
        assert resp.status_code in (401, 422)

    def test_save_endpoint_requires_tma_header(self):
        from webapp.api import app
        client = TestClient(app)
        resp = client.post("/api/save/12345")
        assert resp.status_code in (401, 422)

    def test_clear_endpoint_requires_tma_header(self):
        from webapp.api import app
        client = TestClient(app)
        resp = client.post("/api/clear/12345")
        assert resp.status_code in (401, 422)

    def test_archives_endpoint_requires_tma_header(self):
        from webapp.api import app
        client = TestClient(app)
        resp = client.get("/api/archives/12345")
        assert resp.status_code in (401, 422)

    def test_statistics_endpoint_requires_tma_header(self):
        from webapp.api import app
        client = TestClient(app)
        resp = client.get("/api/statistics/12345")
        assert resp.status_code in (401, 422)

    def test_add_requires_tma_header(self):
        from webapp.api import app
        client = TestClient(app)
        resp = client.post("/api/add", json={"user_id": 111, "product_id": 1, "quantity": 1})
        assert resp.status_code in (401, 422)

    def test_search_requires_tma_header(self):
        from webapp.api import app
        client = TestClient(app)
        resp = client.post("/api/search", json={"query": "test", "user_id": 111, "offset": 0, "limit": 10})
        assert resp.status_code in (401, 422)

    def test_list_uses_tma_identity_not_path_param(self):
        """
        The list endpoint must use the TMA-verified user (user 100), NOT the path user_id (99999).
        If the mocked DB returns data for user 100, the response is success regardless of path.
        """
        from webapp.api import app

        real_user_id = 100
        attacker_user_id = 99999
        headers = self._tma_headers(real_user_id)

        with patch("webapp.routers.client.orm_get_temp_list", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = []
            client = TestClient(app)
            resp = client.get(f"/api/list/{attacker_user_id}", headers=headers)

        # Should succeed (200) and call orm_get_temp_list with the TMA user (100), not 99999
        assert resp.status_code == 200
        # The ORM was called with the TMA user_id, not the attacker user_id
        assert mock_list.called
        called_user_id = mock_list.call_args[0][0] if mock_list.call_args[0] else mock_list.call_args[1].get("user_id")
        assert called_user_id == real_user_id, (
            f"Expected ORM called with TMA user {real_user_id}, got {called_user_id}"
        )

    def test_archives_uses_tma_identity_not_path_param(self):
        """
        The archives endpoint must use TMA-verified user, not path user_id.
        """
        from webapp.api import app

        real_user_id = 200
        attacker_user_id = 77777
        headers = self._tma_headers(real_user_id)

        with patch("webapp.routers.client.fetch_user_archives") as mock_archives:
            mock_archives.return_value = []
            client = TestClient(app)
            resp = client.get(f"/api/archives/{attacker_user_id}", headers=headers)

        assert resp.status_code == 200
        assert mock_archives.called
        called_user_id = mock_archives.call_args[0][0]
        assert called_user_id == real_user_id, (
            f"Expected ORM called with TMA user {real_user_id}, got {called_user_id}"
        )

    def test_add_to_list_uses_tma_identity_not_body_user_id(self):
        """
        POST /add must use TMA-verified user_id, not the user_id in the request body.
        """
        from webapp.api import app

        real_user_id = 300
        attacker_user_id = 88888
        headers = self._tma_headers(real_user_id)

        with patch("webapp.routers.client.orm_add_item_to_temp_list", new_callable=AsyncMock) as mock_add:
            mock_add.return_value = None
            client = TestClient(app)
            resp = client.post(
                "/api/add",
                json={"user_id": attacker_user_id, "product_id": 1, "quantity": 1},
                headers=headers,
            )

        assert resp.status_code == 200
        assert mock_add.called
        called_user_id = mock_add.call_args[1].get("user_id") or mock_add.call_args[0][0]
        assert called_user_id == real_user_id, (
            f"Expected ORM called with TMA user {real_user_id}, got {called_user_id}"
        )


# ---------------------------------------------------------------------------
# Archive download / delete — combined JWT + TMA auth
# ---------------------------------------------------------------------------

class TestArchiveAuthCombined:
    """
    GET /archive/download/{filename} and DELETE /archive/delete/{filename}
    should accept either JWT Bearer or TMA initData (backward compat).
    """

    def test_download_requires_auth(self):
        from webapp.api import app
        client = TestClient(app)
        resp = client.get("/api/archive/download/10_123_20240101_1200.xlsx")
        assert resp.status_code in (401, 422)

    def test_delete_requires_auth(self):
        from webapp.api import app
        client = TestClient(app)
        resp = client.delete("/api/archive/delete/10_123_20240101_1200.xlsx")
        assert resp.status_code in (401, 422)

    def test_download_denied_for_jwt_non_owner(self):
        """A JWT user who is not the file owner must get 403."""
        from webapp.api import app

        requester_id = 111
        owner_id = 222
        filename = f"10_{owner_id}_20240101_1200.xlsx"
        token = _make_jwt_token(user_id=requester_id)
        mock_parsed = {"user_id": owner_id, "department": 10}

        with patch("webapp.routers.client.parse_filename", return_value=mock_parsed):
            client = TestClient(app)
            resp = client.get(
                f"/api/archive/download/{filename}",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 403

    def test_download_denied_for_tma_non_owner(self):
        """A TMA user who is not the file owner must get 403."""
        from webapp.api import app

        requester_id = 333
        owner_id = 444
        filename = f"10_{owner_id}_20240101_1200.xlsx"
        init_data = _make_tma_init_data(user_id=requester_id)
        mock_parsed = {"user_id": owner_id, "department": 10}

        with patch("webapp.routers.client.parse_filename", return_value=mock_parsed):
            client = TestClient(app)
            resp = client.get(
                f"/api/archive/download/{filename}",
                headers={"X-Telegram-Init-Data": init_data},
            )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# User management — combined JWT + TMA auth
# ---------------------------------------------------------------------------

class TestUserManagementAnyAuth:
    """User management endpoints accept both JWT and TMA auth (backward compat)."""

    def test_list_users_rejects_missing_auth(self):
        from webapp.api import app
        client = TestClient(app)
        resp = client.get("/api/admin/user-management/users")
        assert resp.status_code in (401, 422)

    def test_list_users_rejects_invalid_tma(self):
        from webapp.api import app
        client = TestClient(app)
        resp = client.get(
            "/api/admin/user-management/users",
            headers={"X-Telegram-Init-Data": "fake=data&hash=badhash"},
        )
        assert resp.status_code == 401

    def test_list_users_rejects_non_admin_tma(self):
        from webapp.api import app
        init_data = _make_tma_init_data(user_id=555)
        client = TestClient(app)
        with patch("webapp.deps.ADMIN_IDS", []):
            resp = client.get(
                "/api/admin/user-management/users",
                headers={"X-Telegram-Init-Data": init_data},
            )
        assert resp.status_code == 403

    def test_list_users_rejects_non_admin_jwt(self):
        from webapp.api import app
        token = _make_jwt_token(user_id=42, role="user")
        client = TestClient(app)
        with patch("webapp.deps.ADMIN_IDS", []):
            resp = client.get(
                "/api/admin/user-management/users",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 403
