"""Tests for moderator access to import and export endpoints.

These endpoints now require TMA initData (X-Telegram-Init-Data header)
instead of query user_id.
"""
import hashlib
import hmac as _hmac
import io
import json
import time
import urllib.parse
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


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


def test_import_denied_for_regular_user():
    """Звичайний користувач не має доступу до імпорту (TMA auth)."""
    from webapp.api import app

    init_data = _make_tma_init_data(user_id=111)
    with patch("webapp.deps.ADMIN_IDS", []), \
         patch("webapp.routers.admin.ADMIN_IDS", []), \
         patch("webapp.deps.orm_get_user_by_id", new_callable=AsyncMock, return_value=_make_mock_user("user")):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/admin/import",
            files={"file": ("test.xlsx", io.BytesIO(b"dummy"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers={"X-Telegram-Init-Data": init_data},
        )

    assert resp.status_code == 403


def test_import_allowed_for_admin_by_id():
    """Адмін (за ADMIN_IDS) має доступ до імпорту (TMA auth)."""
    from webapp.api import app

    admin_id = 333
    init_data = _make_tma_init_data(user_id=admin_id)
    with patch("webapp.deps.ADMIN_IDS", [admin_id]), \
         patch("webapp.routers.admin.ADMIN_IDS", [admin_id]), \
         patch("webapp.routers.admin.orm_smart_import", new_callable=AsyncMock, return_value=None):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/admin/import",
            files={"file": ("test.xlsx", io.BytesIO(b"dummy"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers={"X-Telegram-Init-Data": init_data},
        )

    # Should not be 403 (file may fail to parse, that's ok)
    assert resp.status_code != 403


def test_import_allowed_for_moderator():
    """Модератор має доступ до імпорту товарів (TMA auth)."""
    from webapp.api import app

    mod_id = 222
    init_data = _make_tma_init_data(user_id=mod_id)
    mock_user = _make_mock_user("moderator")
    with patch("webapp.deps.ADMIN_IDS", []), \
         patch("webapp.routers.admin.ADMIN_IDS", []), \
         patch("webapp.deps.orm_get_user_by_id", new_callable=AsyncMock, return_value=mock_user), \
         patch("webapp.routers.admin.orm_smart_import", new_callable=AsyncMock, return_value=None):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/admin/import",
            files={"file": ("test.xlsx", io.BytesIO(b"dummy"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers={"X-Telegram-Init-Data": init_data},
        )

    # Should not be 403 (file may fail to parse, that's ok)
    assert resp.status_code != 403


def test_export_stock_denied_for_regular_user():
    """Звичайний користувач не має доступу до експорту залишків (TMA auth)."""
    from webapp.api import app

    init_data = _make_tma_init_data(user_id=111)
    with patch("webapp.deps.ADMIN_IDS", []), \
         patch("webapp.routers.admin.ADMIN_IDS", []), \
         patch("webapp.deps.orm_get_user_by_id", new_callable=AsyncMock, return_value=_make_mock_user("user")):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get(
            "/api/admin/export/stock",
            headers={"X-Telegram-Init-Data": init_data},
        )

    assert resp.status_code == 403


def test_export_stock_allowed_for_moderator():
    """Модератор має доступ до експорту залишків (TMA auth)."""
    from webapp.api import app

    mod_id = 222
    init_data = _make_tma_init_data(user_id=mod_id)
    mock_user = _make_mock_user("moderator")
    with patch("webapp.deps.ADMIN_IDS", []), \
         patch("webapp.routers.admin.ADMIN_IDS", []), \
         patch("webapp.deps.orm_get_user_by_id", new_callable=AsyncMock, return_value=mock_user), \
         patch("webapp.routers.admin._create_stock_report_sync", return_value=None):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get(
            "/api/admin/export/stock",
            headers={"X-Telegram-Init-Data": init_data},
        )

    # Should not be 403 (report generation may fail, that's ok)
    assert resp.status_code != 403
