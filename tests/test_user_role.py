from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


def test_user_role_endpoint_returns_default_for_unknown_user():
    """Ендпоінт /api/user/role повертає 'user' для невідомого користувача."""
    from webapp.api import app

    with patch("webapp.routers.client.orm_get_user_by_id", new_callable=AsyncMock, return_value=None):
        client = TestClient(app)
        resp = client.get("/api/user/role", params={"user_id": 999999})

    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "user"


def test_user_role_endpoint_returns_moderator():
    """Ендпоінт /api/user/role повертає 'moderator' для модератора."""
    from webapp.api import app
    from unittest.mock import MagicMock

    mock_user = MagicMock()
    mock_user.role = "moderator"

    with patch("webapp.routers.client.orm_get_user_by_id", new_callable=AsyncMock, return_value=mock_user):
        client = TestClient(app)
        resp = client.get("/api/user/role", params={"user_id": 123})

    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "moderator"


def test_user_role_endpoint_returns_admin():
    """Ендпоінт /api/user/role повертає 'admin' для адміна."""
    from webapp.api import app
    from unittest.mock import MagicMock

    mock_user = MagicMock()
    mock_user.role = "admin"

    with patch("webapp.routers.client.orm_get_user_by_id", new_callable=AsyncMock, return_value=mock_user):
        client = TestClient(app)
        resp = client.get("/api/user/role", params={"user_id": 456})

    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "admin"


def test_user_role_endpoint_requires_user_id():
    """Ендпоінт /api/user/role вимагає параметр user_id."""
    from webapp.api import app

    client = TestClient(app)
    resp = client.get("/api/user/role")

    assert resp.status_code == 422
