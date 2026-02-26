import os
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


def test_moderation_pending_forbidden_for_regular_user():
    """Regular user (role='user') should get 403 on moderation endpoint."""
    from webapp.api import app

    class FakeUser:
        role = "user"

    with patch.dict(os.environ, {"WEBAPP_ADMIN_IDS": ""}), \
         patch("webapp.routers.photos.ADMIN_IDS", []), \
         patch("webapp.routers.photos.async_session") as mock_session:
        session_cm = AsyncMock()
        mock_session.return_value.__aenter__ = AsyncMock(return_value=session_cm)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = FakeUser()
        session_cm.execute = AsyncMock(return_value=mock_result)

        client = TestClient(app)
        resp = client.get("/api/photos/moderation/pending?user_id=999")

    assert resp.status_code == 403


def test_moderation_pending_allowed_for_moderator():
    """User with role='moderator' should get 200 on moderation endpoint."""
    from webapp.api import app

    class FakeUser:
        id = 100
        role = "moderator"
        username = "mod_user"

    with patch.dict(os.environ, {"WEBAPP_ADMIN_IDS": ""}), \
         patch("webapp.routers.photos.ADMIN_IDS", []), \
         patch("webapp.routers.photos.async_session") as mock_session:
        session_cm = AsyncMock()
        mock_session.return_value.__aenter__ = AsyncMock(return_value=session_cm)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

        # First call: _verify_moderator_or_admin lookup
        verify_result = MagicMock()
        verify_result.scalar_one_or_none.return_value = FakeUser()
        # Second call: select pending photos (empty)
        photos_result = MagicMock()
        photos_result.scalars.return_value.all.return_value = []

        session_cm.execute = AsyncMock(side_effect=[verify_result, photos_result])

        client = TestClient(app)
        resp = client.get("/api/photos/moderation/pending?user_id=100")

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["photos"] == []
