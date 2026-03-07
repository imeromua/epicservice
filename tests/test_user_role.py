"""Tests for GET /api/user/role endpoint — now uses TMA initData for auth."""
import hashlib
import hmac as _hmac
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


def test_user_role_endpoint_returns_default_for_unknown_user():
    """Ендпоінт /api/user/role повертає 'user' для невідомого користувача."""
    from webapp.api import app

    init_data = _make_tma_init_data(user_id=999999)
    with patch("webapp.routers.client.orm_get_user_by_id", new_callable=AsyncMock, return_value=None):
        client = TestClient(app)
        resp = client.get("/api/user/role", headers={"X-Telegram-Init-Data": init_data})

    assert resp.status_code == 200
    assert resp.json()["role"] == "user"


def test_user_role_endpoint_returns_moderator():
    """Ендпоінт /api/user/role повертає 'moderator' для модератора."""
    from webapp.api import app

    mock_user = MagicMock()
    mock_user.role = "moderator"
    init_data = _make_tma_init_data(user_id=123)

    with patch("webapp.routers.client.orm_get_user_by_id", new_callable=AsyncMock, return_value=mock_user):
        client = TestClient(app)
        resp = client.get("/api/user/role", headers={"X-Telegram-Init-Data": init_data})

    assert resp.status_code == 200
    assert resp.json()["role"] == "moderator"


def test_user_role_endpoint_returns_admin():
    """Ендпоінт /api/user/role повертає 'admin' для адміна."""
    from webapp.api import app

    mock_user = MagicMock()
    mock_user.role = "admin"
    init_data = _make_tma_init_data(user_id=456)

    with patch("webapp.routers.client.orm_get_user_by_id", new_callable=AsyncMock, return_value=mock_user):
        client = TestClient(app)
        resp = client.get("/api/user/role", headers={"X-Telegram-Init-Data": init_data})

    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


def test_user_role_endpoint_requires_tma_header():
    """Ендпоінт /api/user/role вимагає X-Telegram-Init-Data header (більше не query param)."""
    from webapp.api import app

    client = TestClient(app)
    # No header → 422 (missing required header)
    resp = client.get("/api/user/role")
    assert resp.status_code in (401, 422)
