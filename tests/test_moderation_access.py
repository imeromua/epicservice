from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


def _make_mock_user(role="user"):
    u = MagicMock()
    u.role = role
    return u


def _make_jwt_token(user_id: int, role: str = "user") -> str:
    """Generate a real JWT token for testing."""
    from webapp.routers.auth import create_token
    return create_token(user_id, f"user_{user_id}", role, "access")


def test_moderation_pending_denied_for_regular_user():
    """Звичайний користувач не має доступу до модерації фото."""
    from webapp.api import app

    mock_user = _make_mock_user("user")
    token = _make_jwt_token(111, "user")

    with patch("webapp.deps.ADMIN_IDS", []), \
         patch("webapp.deps.orm_get_user_by_id", new_callable=AsyncMock, return_value=mock_user):
        client = TestClient(app)
        resp = client.get(
            "/api/photos/moderation/pending",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 403


def test_moderation_pending_allowed_for_moderator():
    """Модератор має доступ до модерації фото."""
    from webapp.api import app

    mock_user = _make_mock_user("moderator")
    token = _make_jwt_token(222, "moderator")

    with patch("webapp.deps.ADMIN_IDS", []), \
         patch("webapp.deps.orm_get_user_by_id", new_callable=AsyncMock, return_value=mock_user), \
         patch("webapp.routers.photos.async_session") as mock_session_cls:
        mock_session = AsyncMock()
        mock_result_photos = MagicMock()
        mock_result_photos.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result_photos)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = mock_session

        client = TestClient(app)
        resp = client.get(
            "/api/photos/moderation/pending",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


def test_moderation_pending_allowed_for_admin_by_id():
    """Адмін (за ADMIN_IDS) має доступ до модерації фото."""
    from webapp.api import app

    token = _make_jwt_token(333, "admin")

    with patch("webapp.deps.ADMIN_IDS", [333]), \
         patch("webapp.routers.photos.async_session") as mock_session_cls:
        mock_session = AsyncMock()
        mock_result_photos = MagicMock()
        mock_result_photos.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result_photos)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = mock_session

        client = TestClient(app)
        resp = client.get(
            "/api/photos/moderation/pending",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True

