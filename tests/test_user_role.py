from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


def test_user_role_endpoint_returns_default_for_unknown_user():
    """Unknown user_id should return role='user'."""
    from webapp.api import app

    with patch("webapp.routers.client.orm_get_user_by_id", new_callable=AsyncMock, return_value=None):
        client = TestClient(app)
        resp = client.get("/api/user/role?user_id=999999")

    assert resp.status_code == 200
    assert resp.json() == {"role": "user"}


def test_user_role_endpoint_returns_moderator():
    """User with role='moderator' should get that role back."""
    from webapp.api import app

    class FakeUser:
        role = "moderator"

    with patch("webapp.routers.client.orm_get_user_by_id", new_callable=AsyncMock, return_value=FakeUser()):
        client = TestClient(app)
        resp = client.get("/api/user/role?user_id=123")

    assert resp.status_code == 200
    assert resp.json() == {"role": "moderator"}


def test_user_role_endpoint_returns_admin():
    """User with role='admin' should get that role back."""
    from webapp.api import app

    class FakeUser:
        role = "admin"

    with patch("webapp.routers.client.orm_get_user_by_id", new_callable=AsyncMock, return_value=FakeUser()):
        client = TestClient(app)
        resp = client.get("/api/user/role?user_id=456")

    assert resp.status_code == 200
    assert resp.json() == {"role": "admin"}
