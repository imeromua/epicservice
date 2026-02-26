from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


def _make_mock_user(role="user"):
    u = MagicMock()
    u.role = role
    return u


def test_moderation_pending_denied_for_regular_user():
    """Звичайний користувач не має доступу до модерації фото."""
    from webapp.api import app

    mock_user = _make_mock_user("user")
    with patch("webapp.routers.photos.ADMIN_IDS", []), \
         patch("webapp.routers.photos.async_session") as mock_session_cls:
        # Setup async context manager for session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = mock_session

        client = TestClient(app)
        resp = client.get("/api/photos/moderation/pending", params={"user_id": 111})

    assert resp.status_code == 403


def test_moderation_pending_allowed_for_moderator():
    """Модератор має доступ до модерації фото."""
    from webapp.api import app

    mock_user = _make_mock_user("moderator")
    with patch("webapp.routers.photos.ADMIN_IDS", []), \
         patch("webapp.routers.photos.async_session") as mock_session_cls:
        mock_session = AsyncMock()

        # First call: _is_admin_or_moderator check
        mock_result_role = MagicMock()
        mock_result_role.scalar_one_or_none.return_value = mock_user

        # Second call: actual query for pending photos
        mock_result_photos = MagicMock()
        mock_result_photos.scalars.return_value.all.return_value = []

        mock_session.execute = AsyncMock(side_effect=[mock_result_role, mock_result_photos])
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = mock_session

        client = TestClient(app)
        resp = client.get("/api/photos/moderation/pending", params={"user_id": 222})

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


def test_moderation_pending_allowed_for_admin_by_id():
    """Адмін (за ADMIN_IDS) має доступ до модерації фото."""
    from webapp.api import app

    with patch("webapp.routers.photos.ADMIN_IDS", [333]), \
         patch("webapp.routers.photos.async_session") as mock_session_cls:
        mock_session = AsyncMock()
        mock_result_photos = MagicMock()
        mock_result_photos.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result_photos)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = mock_session

        client = TestClient(app)
        resp = client.get("/api/photos/moderation/pending", params={"user_id": 333})

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
