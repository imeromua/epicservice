"""Tests for the POST /api/admin/subtract-collected endpoint.

Updated to use TMA initData authentication (X-Telegram-Init-Data header)
instead of user_id query parameter.
"""
import hashlib
import hmac as _hmac
import io
import json
import time
import urllib.parse
from unittest.mock import AsyncMock, MagicMock, patch

import openpyxl
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Test helpers
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


def _make_xlsx(rows: list) -> bytes:
    """Create a minimal .xlsx file with the given rows (list of (article, qty) tuples)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _make_file(rows):
    return ("test.xlsx", _make_xlsx(rows), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def _tma_headers(user_id: int) -> dict:
    return {"X-Telegram-Init-Data": _make_tma_init_data(user_id)}


# ---------------------------------------------------------------------------
# Access control tests
# ---------------------------------------------------------------------------

def test_subtract_denied_for_regular_user():
    """Regular user gets 403 (TMA auth)."""
    from webapp.api import app

    init_data = _make_tma_init_data(user_id=111)
    with patch("webapp.deps.ADMIN_IDS", []), \
         patch("webapp.routers.admin.ADMIN_IDS", []), \
         patch("webapp.deps.orm_get_user_by_id", new_callable=AsyncMock, return_value=_make_mock_user("user")):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/admin/subtract-collected",
            files={"file": _make_file([("ART1", 5)])},
            headers={"X-Telegram-Init-Data": init_data},
        )
    assert resp.status_code == 403


def test_subtract_allowed_for_admin():
    """Admin (by ADMIN_IDS) is not blocked by 403 (TMA auth)."""
    from webapp.api import app

    admin_id = 999
    init_data = _make_tma_init_data(user_id=admin_id)

    mock_session = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    scalar_result = MagicMock()
    scalar_result.scalar.return_value = 0
    mock_session.execute = AsyncMock(return_value=scalar_result)
    mock_session.begin = MagicMock(
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=None),
            __aexit__=AsyncMock(return_value=False),
        )
    )

    with patch("webapp.deps.ADMIN_IDS", [admin_id]), \
         patch("webapp.routers.admin.ADMIN_IDS", [admin_id]), \
         patch("webapp.routers.admin.orm_get_users_with_active_lists", new_callable=AsyncMock, return_value=[]), \
         patch("webapp.routers.admin.async_session", return_value=mock_ctx):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/admin/subtract-collected",
            files={"file": _make_file([("ART1", 5)])},
            headers={"X-Telegram-Init-Data": init_data},
        )
    assert resp.status_code != 403


# ---------------------------------------------------------------------------
# Blocking checks
# ---------------------------------------------------------------------------

def test_subtract_blocked_by_active_list():
    """Returns 409 with reason=active_list when there are active lists."""
    from webapp.api import app

    admin_id = 999
    init_data = _make_tma_init_data(user_id=admin_id)

    with patch("webapp.deps.ADMIN_IDS", [admin_id]), \
         patch("webapp.routers.admin.ADMIN_IDS", [admin_id]), \
         patch("webapp.routers.admin.orm_get_users_with_active_lists", new_callable=AsyncMock, return_value=[(1, 2)]):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/admin/subtract-collected",
            files={"file": _make_file([("ART1", 5)])},
            headers={"X-Telegram-Init-Data": init_data},
        )
    assert resp.status_code == 409
    data = resp.json()
    assert data["blocked"] is True
    assert data["reason"] == "active_list"


def test_subtract_blocked_by_reserved():
    """Returns 409 with reason=reserved_exists when reserves > 0."""
    from webapp.api import app

    admin_id = 999
    init_data = _make_tma_init_data(user_id=admin_id)

    mock_session = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    scalar_result = MagicMock()
    scalar_result.scalar.return_value = 3
    mock_session.execute = AsyncMock(return_value=scalar_result)

    with patch("webapp.deps.ADMIN_IDS", [admin_id]), \
         patch("webapp.routers.admin.ADMIN_IDS", [admin_id]), \
         patch("webapp.routers.admin.orm_get_users_with_active_lists", new_callable=AsyncMock, return_value=[]), \
         patch("webapp.routers.admin.async_session", return_value=mock_ctx):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/admin/subtract-collected",
            files={"file": _make_file([("ART1", 5)])},
            headers={"X-Telegram-Init-Data": init_data},
        )
    assert resp.status_code == 409
    data = resp.json()
    assert data["blocked"] is True
    assert data["reason"] == "reserved_exists"


# ---------------------------------------------------------------------------
# File format validation
# ---------------------------------------------------------------------------

def test_subtract_rejects_non_xlsx():
    """Returns 400 for non-xlsx files."""
    from webapp.api import app

    admin_id = 999
    init_data = _make_tma_init_data(user_id=admin_id)

    with patch("webapp.deps.ADMIN_IDS", [admin_id]), \
         patch("webapp.routers.admin.ADMIN_IDS", [admin_id]):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/admin/subtract-collected",
            files={"file": ("test.csv", b"a,b\n", "text/csv")},
            headers={"X-Telegram-Init-Data": init_data},
        )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Logic tests
# ---------------------------------------------------------------------------

def _make_mock_product(article, qty, active=True):
    p = MagicMock()
    p.артикул = article
    p.кількість = str(qty)
    p.активний = active
    return p


def test_subtract_success_basic():
    """Successful subtraction returns success=True with correct summary."""
    from webapp.api import app

    admin_id = 999
    init_data = _make_tma_init_data(user_id=admin_id)
    product = _make_mock_product("ART1", 20)

    mock_session = MagicMock()

    async def execute(stmt):
        stmt_str = str(stmt)
        r = MagicMock()
        if "відкладено" in stmt_str or "COUNT" in stmt_str.upper():
            r.scalar.return_value = 0
        else:
            r.scalar_one_or_none.return_value = product
        return r

    mock_session.execute = execute

    async def begin_aenter(self):
        pass

    async def begin_aexit(self, *args):
        pass

    mock_begin = MagicMock()
    mock_begin.__aenter__ = begin_aenter
    mock_begin.__aexit__ = begin_aexit
    mock_session.begin = MagicMock(return_value=mock_begin)

    class FakeAsyncSessionCtx:
        async def __aenter__(self):
            return mock_session

        async def __aexit__(self, *args):
            pass

    class FakeAsyncSession:
        def __call__(self):
            return FakeAsyncSessionCtx()

    with patch("webapp.deps.ADMIN_IDS", [admin_id]), \
         patch("webapp.routers.admin.ADMIN_IDS", [admin_id]), \
         patch("webapp.routers.admin.orm_get_users_with_active_lists", new_callable=AsyncMock, return_value=[]), \
         patch("webapp.routers.admin.async_session", FakeAsyncSession()):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/admin/subtract-collected",
            files={"file": _make_file([("ART1", 5)])},
            headers={"X-Telegram-Init-Data": init_data},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "summary" in data
    assert "details" in data


def test_subtract_skipped_invalid_rows():
    """Invalid rows (empty article or bad qty) are counted in skipped_invalid."""
    from webapp.api import app

    admin_id = 999
    init_data = _make_tma_init_data(user_id=admin_id)
    mock_session = MagicMock()

    async def execute(stmt):
        r = MagicMock()
        r.scalar.return_value = 0
        r.scalar_one_or_none.return_value = None
        return r

    mock_session.execute = execute

    async def begin_aenter(self):
        pass

    async def begin_aexit(self, *args):
        pass

    mock_begin = MagicMock()
    mock_begin.__aenter__ = begin_aenter
    mock_begin.__aexit__ = begin_aexit
    mock_session.begin = MagicMock(return_value=mock_begin)

    class FakeAsyncSessionCtx:
        async def __aenter__(self):
            return mock_session

        async def __aexit__(self, *args):
            pass

    class FakeAsyncSession:
        def __call__(self):
            return FakeAsyncSessionCtx()

    # Row 1: empty article, Row 2: bad qty, Row 3: qty=0
    rows = [
        ("", 5),
        ("ART2", "abc"),
        ("ART3", 0),
        ("ART4", 3),
    ]

    with patch("webapp.deps.ADMIN_IDS", [admin_id]), \
         patch("webapp.routers.admin.ADMIN_IDS", [admin_id]), \
         patch("webapp.routers.admin.orm_get_users_with_active_lists", new_callable=AsyncMock, return_value=[]), \
         patch("webapp.routers.admin.async_session", FakeAsyncSession()):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/admin/subtract-collected",
            files={"file": _make_file(rows)},
            headers={"X-Telegram-Init-Data": init_data},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    # 3 invalid rows (empty article, bad qty, qty=0)
    assert data["summary"]["skipped_invalid"] == 3
    assert data["summary"]["rows_valid"] == 1
    assert len(data["details"]["skipped_invalid"]) == 3
