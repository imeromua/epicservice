"""
Tests for the hardened authorization layer.

Covers:
- Admin danger zone endpoints (require JWT Bearer admin token)
- User management endpoints (require JWT Bearer admin token)
- Photo delete (only author or admin/moderator)
- Archive download (only file owner)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_jwt_token(user_id: int, role: str = "user") -> str:
    """Generate a real JWT token for testing."""
    from webapp.routers.auth import create_token
    return create_token(user_id, f"user_{user_id}", role, "access")


def _make_mock_user(user_id: int = 1, role: str = "user", status: str = "active"):
    u = MagicMock()
    u.id = user_id
    u.role = role
    u.status = status
    return u


# ---------------------------------------------------------------------------
# Admin Danger Zone — require JWT Bearer admin token
# ---------------------------------------------------------------------------

class TestDangerZoneAuth:
    """Danger zone endpoints must reject requests without a valid admin JWT."""

    DANGER_ENDPOINTS = [
        "/api/admin/danger/clear-database",
        "/api/admin/danger/delete-all-photos",
        "/api/admin/danger/delete-all-archives",
        "/api/admin/danger/full-wipe",
    ]

    def test_danger_endpoints_reject_missing_token(self):
        from webapp.api import app
        client = TestClient(app)
        for endpoint in self.DANGER_ENDPOINTS:
            resp = client.post(endpoint)
            assert resp.status_code in (401, 422), (
                f"Expected 401/422 without token, got {resp.status_code} for {endpoint}"
            )

    def test_danger_endpoints_reject_non_admin_jwt(self):
        """A valid JWT for a non-admin user must be rejected with 403."""
        from webapp.api import app
        token = _make_jwt_token(user_id=999, role="user")
        client = TestClient(app)
        with patch("webapp.deps.ADMIN_IDS", []):
            for endpoint in self.DANGER_ENDPOINTS:
                resp = client.post(endpoint, headers={"Authorization": f"Bearer {token}"})
                assert resp.status_code == 403, (
                    f"Expected 403 for non-admin, got {resp.status_code} for {endpoint}"
                )

    def test_danger_endpoints_reject_invalid_token(self):
        """A malformed / bogus token must be rejected with 401."""
        from webapp.api import app
        client = TestClient(app)
        for endpoint in self.DANGER_ENDPOINTS:
            resp = client.post(endpoint, headers={"Authorization": "Bearer not-a-real-token"})
            assert resp.status_code == 401, (
                f"Expected 401 for bad token, got {resp.status_code} for {endpoint}"
            )


# ---------------------------------------------------------------------------
# User Management — require JWT Bearer admin token
# ---------------------------------------------------------------------------

class TestUserManagementAuth:
    """User management endpoints must reject non-admin callers."""

    def test_list_users_rejects_missing_token(self):
        from webapp.api import app
        client = TestClient(app)
        resp = client.get("/api/admin/user-management/users")
        # Without Authorization header → 422 (missing required header) or 401
        assert resp.status_code in (401, 422)

    def test_list_users_rejects_non_admin_jwt(self):
        from webapp.api import app
        token = _make_jwt_token(user_id=42, role="user")
        with patch("webapp.deps.ADMIN_IDS", []):
            client = TestClient(app)
            resp = client.get(
                "/api/admin/user-management/users",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 403

    def test_approve_user_rejects_non_admin_jwt(self):
        from webapp.api import app
        token = _make_jwt_token(user_id=42, role="user")
        with patch("webapp.deps.ADMIN_IDS", []):
            client = TestClient(app)
            resp = client.post(
                "/api/admin/user-management/approve",
                json={"target_user_id": 99},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 403

    def test_block_user_rejects_non_admin_jwt(self):
        from webapp.api import app
        token = _make_jwt_token(user_id=42, role="user")
        with patch("webapp.deps.ADMIN_IDS", []):
            client = TestClient(app)
            resp = client.post(
                "/api/admin/user-management/block",
                json={"target_user_id": 99},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 403

    def test_unblock_user_rejects_non_admin_jwt(self):
        from webapp.api import app
        token = _make_jwt_token(user_id=42, role="user")
        with patch("webapp.deps.ADMIN_IDS", []):
            client = TestClient(app)
            resp = client.post(
                "/api/admin/user-management/unblock",
                json={"target_user_id": 99},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 403

    def test_set_role_rejects_non_admin_jwt(self):
        from webapp.api import app
        token = _make_jwt_token(user_id=42, role="user")
        with patch("webapp.deps.ADMIN_IDS", []):
            client = TestClient(app)
            resp = client.post(
                "/api/admin/user-management/role",
                json={"target_user_id": 99, "role": "moderator"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Photo Delete — only author or admin/moderator
# ---------------------------------------------------------------------------

class TestPhotoDeleteAuth:
    """DELETE /api/photos/{photo_id} must enforce author-or-admin-or-moderator."""

    def _make_photo(self, photo_id: int, uploaded_by: int):
        photo = MagicMock()
        photo.id = photo_id
        photo.uploaded_by = uploaded_by
        photo.file_path = f"uploads/photos/{uploaded_by}/photo_0.jpg"
        return photo

    def test_delete_photo_requires_token(self):
        """No Authorization header → 422 (missing required header)."""
        from webapp.api import app
        client = TestClient(app)
        resp = client.delete("/api/photos/1")
        assert resp.status_code in (401, 422)

    def test_delete_photo_denied_for_non_author(self):
        """A user who is not the photo author and not admin must get 403."""
        from webapp.api import app

        attacker_id = 777
        author_id = 999
        photo = self._make_photo(photo_id=1, uploaded_by=author_id)

        token = _make_jwt_token(user_id=attacker_id, role="user")
        mock_db_user = _make_mock_user(user_id=attacker_id, role="user")

        with patch("webapp.deps.ADMIN_IDS", []), \
             patch("webapp.routers.photos.ADMIN_IDS", []), \
             patch("webapp.routers.photos.async_session") as mock_session_cls:

            mock_session = AsyncMock()
            # First execute: select photo by id
            mock_photo_result = MagicMock()
            mock_photo_result.scalar_one_or_none.return_value = photo
            # Second execute: select user by id (for DB role check)
            mock_user_result = MagicMock()
            mock_user_result.scalar_one_or_none.return_value = mock_db_user
            mock_session.execute = AsyncMock(
                side_effect=[mock_photo_result, mock_user_result]
            )
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_session

            client = TestClient(app)
            resp = client.delete(
                "/api/photos/1",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 403

    def test_delete_photo_allowed_for_author(self):
        """The photo author can delete their own photo."""
        from webapp.api import app

        author_id = 123
        photo = self._make_photo(photo_id=5, uploaded_by=author_id)

        token = _make_jwt_token(user_id=author_id, role="user")

        with patch("webapp.deps.ADMIN_IDS", []), \
             patch("webapp.routers.photos.ADMIN_IDS", []), \
             patch("webapp.routers.photos.async_session") as mock_session_cls, \
             patch("webapp.routers.photos.Path") as mock_path_cls:

            # Make the file path appear to not exist (so unlink is skipped)
            mock_full_path = MagicMock()
            mock_full_path.exists.return_value = False
            mock_path_cls.return_value.__truediv__ = MagicMock(return_value=mock_full_path)
            mock_path_cls.return_value.__rtruediv__ = MagicMock(return_value=mock_full_path)

            mock_session = AsyncMock()
            mock_photo_result = MagicMock()
            mock_photo_result.scalar_one_or_none.return_value = photo
            mock_session.execute = AsyncMock(return_value=mock_photo_result)
            mock_session.delete = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_session

            client = TestClient(app)
            resp = client.delete(
                "/api/photos/5",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_delete_photo_allowed_for_admin(self):
        """An admin (in ADMIN_IDS) can delete any photo."""
        from webapp.api import app

        admin_id = 1001
        author_id = 999
        photo = self._make_photo(photo_id=7, uploaded_by=author_id)

        token = _make_jwt_token(user_id=admin_id, role="admin")

        with patch("webapp.deps.ADMIN_IDS", [admin_id]), \
             patch("webapp.routers.photos.ADMIN_IDS", [admin_id]), \
             patch("webapp.routers.photos.async_session") as mock_session_cls, \
             patch("webapp.routers.photos.Path") as mock_path_cls:

            mock_full_path = MagicMock()
            mock_full_path.exists.return_value = False
            mock_path_cls.return_value.__truediv__ = MagicMock(return_value=mock_full_path)

            mock_session = AsyncMock()
            mock_photo_result = MagicMock()
            mock_photo_result.scalar_one_or_none.return_value = photo
            mock_session.execute = AsyncMock(return_value=mock_photo_result)
            mock_session.delete = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_session

            client = TestClient(app)
            resp = client.delete(
                "/api/photos/7",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        assert resp.json()["success"] is True


# ---------------------------------------------------------------------------
# Archive Download — only file owner
# ---------------------------------------------------------------------------

class TestArchiveDownloadAuth:
    """GET /api/archive/download/{filename} must enforce file ownership."""

    def test_download_archive_requires_token(self):
        """No Authorization header → 422 (missing required header)."""
        from webapp.api import app
        client = TestClient(app)
        resp = client.get("/api/archive/download/10_123456_20240101_1200.xlsx")
        assert resp.status_code in (401, 422)

    def test_download_archive_denied_for_non_owner(self):
        """A user trying to download another user's archive must get 403."""
        from webapp.api import app

        requester_id = 111
        owner_id = 222
        filename = f"10_{owner_id}_20240101_1200.xlsx"

        token = _make_jwt_token(user_id=requester_id, role="user")

        mock_parsed = {"user_id": owner_id, "department": "10"}

        with patch("webapp.routers.client.parse_filename", return_value=mock_parsed):
            client = TestClient(app)
            resp = client.get(
                f"/api/archive/download/{filename}",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 403

    def test_download_archive_denied_for_missing_token(self):
        """No token → 401 or 422."""
        from webapp.api import app
        client = TestClient(app)
        resp = client.get("/api/archive/download/10_222_20240101_1200.xlsx")
        assert resp.status_code in (401, 422)
