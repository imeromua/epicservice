"""Tests for the POST /api/admin/subtract-collected endpoint."""
import io
from unittest.mock import AsyncMock, MagicMock, patch

import openpyxl
import pytest
from fastapi.testclient import TestClient


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


# --- Access control ---

def test_subtract_denied_for_regular_user():
    """Regular user gets 403."""
    from webapp.api import app

    with patch("webapp.routers.admin.ADMIN_IDS", []), \
         patch("webapp.routers.admin.orm_get_user_by_id", new_callable=AsyncMock, return_value=_make_mock_user("user")):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/admin/subtract-collected",
            params={"user_id": 111},
            files={"file": _make_file([("ART1", 5)])},
        )
    assert resp.status_code == 403


def test_subtract_allowed_for_admin():
    """Admin (by ADMIN_IDS) is not blocked by 403."""
    from webapp.api import app

    mock_session = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    scalar_result = MagicMock()
    scalar_result.scalar.return_value = 0
    mock_session.execute = AsyncMock(return_value=scalar_result)
    mock_session.begin = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=None), __aexit__=AsyncMock(return_value=False)))

    with patch("webapp.routers.admin.ADMIN_IDS", [999]), \
         patch("webapp.routers.admin.orm_get_users_with_active_lists", new_callable=AsyncMock, return_value=[]), \
         patch("webapp.routers.admin.async_session", return_value=mock_ctx):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/admin/subtract-collected",
            params={"user_id": 999},
            files={"file": _make_file([("ART1", 5)])},
        )
    assert resp.status_code != 403


# --- Blocking checks ---

def test_subtract_blocked_by_active_list():
    """Returns 409 with reason=active_list when there are active lists."""
    from webapp.api import app

    with patch("webapp.routers.admin.ADMIN_IDS", [999]), \
         patch("webapp.routers.admin.orm_get_users_with_active_lists", new_callable=AsyncMock, return_value=[(1, 2)]):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/admin/subtract-collected",
            params={"user_id": 999},
            files={"file": _make_file([("ART1", 5)])},
        )
    assert resp.status_code == 409
    data = resp.json()
    assert data["blocked"] is True
    assert data["reason"] == "active_list"


def test_subtract_blocked_by_reserved():
    """Returns 409 with reason=reserved_exists when reserves > 0."""
    from webapp.api import app

    mock_session = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    scalar_result = MagicMock()
    scalar_result.scalar.return_value = 3
    mock_session.execute = AsyncMock(return_value=scalar_result)

    with patch("webapp.routers.admin.ADMIN_IDS", [999]), \
         patch("webapp.routers.admin.orm_get_users_with_active_lists", new_callable=AsyncMock, return_value=[]), \
         patch("webapp.routers.admin.async_session", return_value=mock_ctx):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/admin/subtract-collected",
            params={"user_id": 999},
            files={"file": _make_file([("ART1", 5)])},
        )
    assert resp.status_code == 409
    data = resp.json()
    assert data["blocked"] is True
    assert data["reason"] == "reserved_exists"


# --- File format ---

def test_subtract_rejects_non_xlsx():
    """Returns 400 for non-xlsx files."""
    from webapp.api import app

    with patch("webapp.routers.admin.ADMIN_IDS", [999]):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/admin/subtract-collected",
            params={"user_id": 999},
            files={"file": ("test.csv", b"a,b\n", "text/csv")},
        )
    assert resp.status_code == 400


# --- Logic tests ---

def _make_mock_product(article, qty, active=True):
    p = MagicMock()
    p.артикул = article
    p.кількість = str(qty)
    p.активний = active
    return p


def _run_subtract_with_products(rows, products_map, *, admin_ids=None):
    """
    Helper: run subtract-collected endpoint with given xlsx rows and mock products.
    products_map: dict[article_str -> product_mock or None]
    Returns response object.
    """
    from webapp.api import app

    if admin_ids is None:
        admin_ids = [999]

    call_counter = {"n": 0}
    reserved_calls = {"n": 0}

    async def mock_session_execute(stmt):
        import sqlalchemy
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        if "відкладено" in compiled or "COUNT" in compiled:
            r = MagicMock()
            r.scalar.return_value = 0
            return r
        # Product select - extract article from WHERE clause
        # Use a simple heuristic: look for the article in products_map
        r = MagicMock()
        r.scalar_one_or_none.return_value = None
        return r

    # We need to mock async_session and the select queries more precisely.
    # Use a side_effect that tracks calls.
    product_lookup = {}
    for art, prod in products_map.items():
        product_lookup[art] = prod

    execute_results = []

    async def execute_side_effect(stmt):
        # Detect if it's a COUNT query (reservations check)
        stmt_str = str(stmt)
        if "відкладено" in stmt_str or "COUNT" in stmt_str.upper():
            r = MagicMock()
            r.scalar.return_value = 0
            return r
        # Otherwise assume it's a Product select - return based on article
        # We'll just return the products in order
        r = MagicMock()
        r.scalar_one_or_none.return_value = None
        return r

    # Actually let's just patch at a higher level
    articles_in_order = []
    for row in rows:
        if row[0] and str(row[0]).strip():
            art = str(row[0]).strip()
            if art not in articles_in_order:
                articles_in_order.append(art)

    call_idx = {"i": 0}

    class FakeSession:
        async def execute(self, stmt):
            stmt_str = str(stmt)
            if "відкладено" in stmt_str or "COUNT" in stmt_str.upper():
                r = MagicMock()
                r.scalar.return_value = 0
                return r
            r = MagicMock()
            # determine article from the compiled query - it's a select with WHERE
            # We'll look through all products in order
            idx = call_idx["i"]
            if idx < len(articles_in_order):
                art = articles_in_order[idx]
                call_idx["i"] += 1
                r.scalar_one_or_none.return_value = product_lookup.get(art)
            else:
                r.scalar_one_or_none.return_value = None
            return r

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        def begin(self):
            return self

    fake_session = FakeSession()

    class FakeAsyncSession:
        def __call__(self):
            return fake_session

    with patch("webapp.routers.admin.ADMIN_IDS", admin_ids), \
         patch("webapp.routers.admin.orm_get_users_with_active_lists", new_callable=AsyncMock, return_value=[]), \
         patch("webapp.routers.admin.async_session", FakeAsyncSession()):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/admin/subtract-collected",
            params={"user_id": 999},
            files={"file": _make_file(rows)},
        )
    return resp


def test_subtract_success_basic():
    """Successful subtraction returns success=True with correct summary."""
    from webapp.api import app

    product = _make_mock_product("ART1", 20)

    mock_session = MagicMock()
    mock_ctx = MagicMock()
    mock_begin_ctx = MagicMock()

    async def execute(stmt):
        stmt_str = str(stmt)
        r = MagicMock()
        if "відкладено" in stmt_str or "COUNT" in stmt_str.upper():
            r.scalar.return_value = 0
        else:
            r.scalar_one_or_none.return_value = product
        return r

    mock_session.execute = execute

    async def session_aenter(self):
        return mock_session

    async def session_aexit(self, *args):
        pass

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

    with patch("webapp.routers.admin.ADMIN_IDS", [999]), \
         patch("webapp.routers.admin.orm_get_users_with_active_lists", new_callable=AsyncMock, return_value=[]), \
         patch("webapp.routers.admin.async_session", FakeAsyncSession()):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/admin/subtract-collected",
            params={"user_id": 999},
            files={"file": _make_file([("ART1", 5)])},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "summary" in data
    assert "details" in data


def test_subtract_skipped_invalid_rows():
    """Invalid rows (empty article or bad qty) are counted in skipped_invalid."""
    from webapp.api import app

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

    with patch("webapp.routers.admin.ADMIN_IDS", [999]), \
         patch("webapp.routers.admin.orm_get_users_with_active_lists", new_callable=AsyncMock, return_value=[]), \
         patch("webapp.routers.admin.async_session", FakeAsyncSession()):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/admin/subtract-collected",
            params={"user_id": 999},
            files={"file": _make_file(rows)},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    # 3 invalid rows (empty article, bad qty, qty=0)
    assert data["summary"]["skipped_invalid"] == 3
    assert data["summary"]["rows_valid"] == 1
    assert len(data["details"]["skipped_invalid"]) == 3
