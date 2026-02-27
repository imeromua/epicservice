"""Tests for moderator access to import and export endpoints."""
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


def _make_mock_user(role="user"):
    u = MagicMock()
    u.role = role
    return u


def test_import_denied_for_regular_user():
    """Звичайний користувач не має доступу до імпорту."""
    from webapp.api import app

    with patch("webapp.routers.admin.ADMIN_IDS", []), \
         patch("webapp.routers.admin.orm_get_user_by_id", new_callable=AsyncMock, return_value=_make_mock_user("user")):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/admin/import",
            params={"user_id": 111},
            files={"file": ("test.xlsx", BytesIO(b"dummy"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )

    assert resp.status_code == 403


def test_import_allowed_for_admin_by_id():
    """Адмін (за ADMIN_IDS) має доступ до імпорту."""
    from webapp.api import app

    mock_result = MagicMock()
    mock_result.success = False

    with patch("webapp.routers.admin.ADMIN_IDS", [333]), \
         patch("webapp.routers.admin.orm_smart_import", new_callable=AsyncMock, return_value=None):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/admin/import",
            params={"user_id": 333},
            files={"file": ("test.xlsx", BytesIO(b"dummy"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )

    # Should not be 403 (file may fail to parse, that's ok)
    assert resp.status_code != 403


def test_import_allowed_for_moderator():
    """Модератор має доступ до імпорту товарів."""
    from webapp.api import app

    with patch("webapp.routers.admin.ADMIN_IDS", []), \
         patch("webapp.routers.admin.orm_get_user_by_id", new_callable=AsyncMock, return_value=_make_mock_user("moderator")), \
         patch("webapp.routers.admin.orm_smart_import", new_callable=AsyncMock, return_value=None):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/admin/import",
            params={"user_id": 222},
            files={"file": ("test.xlsx", BytesIO(b"dummy"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )

    # Should not be 403 (file may fail to parse, that's ok)
    assert resp.status_code != 403


def test_export_stock_denied_for_regular_user():
    """Звичайний користувач не має доступу до експорту залишків."""
    from webapp.api import app

    with patch("webapp.routers.admin.ADMIN_IDS", []), \
         patch("webapp.routers.admin.orm_get_user_by_id", new_callable=AsyncMock, return_value=_make_mock_user("user")):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/admin/export/stock", params={"user_id": 111})

    assert resp.status_code == 403


def test_export_stock_allowed_for_moderator():
    """Модератор має доступ до експорту залишків."""
    from webapp.api import app

    with patch("webapp.routers.admin.ADMIN_IDS", []), \
         patch("webapp.routers.admin.orm_get_user_by_id", new_callable=AsyncMock, return_value=_make_mock_user("moderator")), \
         patch("webapp.routers.admin._create_stock_report_sync", return_value=None):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/admin/export/stock", params={"user_id": 222})

    # Should not be 403 (report generation may fail, that's ok)
    assert resp.status_code != 403
