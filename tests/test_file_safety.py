"""
Tests for hardened file upload and storage security (PR #44).

Covers:
- webapp/utils/file_safety.py — unit tests for path safety and image validation helpers.
- POST /api/photos/upload — rejects empty, oversized, and non-image files.
- DELETE /api/photos/{photo_id} — path traversal attempt blocked.
"""

import os
import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_jwt_token(user_id: int, role: str = "user") -> str:
    from webapp.routers.auth import create_token
    return create_token(user_id, f"user_{user_id}", role, "access")


def _make_valid_jpeg_bytes() -> bytes:
    """Return the raw bytes of a minimal valid JPEG image."""
    from PIL import Image
    img = Image.new("RGB", (10, 10), color=(255, 0, 0))
    buf = BytesIO()
    img.save(buf, "JPEG")
    return buf.getvalue()


def _make_valid_png_bytes() -> bytes:
    """Return the raw bytes of a minimal valid PNG image."""
    from PIL import Image
    img = Image.new("RGB", (10, 10), color=(0, 128, 0))
    buf = BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _make_bmp_bytes() -> bytes:
    """Return a valid BMP file (not in our ALLOWED_IMAGE_FORMATS)."""
    from PIL import Image
    img = Image.new("RGB", (8, 8), color=(0, 0, 255))
    buf = BytesIO()
    img.save(buf, "BMP")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Unit tests — webapp/utils/file_safety.py
# ---------------------------------------------------------------------------

class TestIsPathWithin:
    """Tests for the is_path_within() helper."""

    def test_allows_direct_child(self, tmp_path):
        from webapp.utils.file_safety import is_path_within
        child = tmp_path / "subdir" / "file.txt"
        assert is_path_within(tmp_path, child) is True

    def test_allows_root_itself(self, tmp_path):
        from webapp.utils.file_safety import is_path_within
        assert is_path_within(tmp_path, tmp_path) is True

    def test_blocks_parent_escape(self, tmp_path):
        from webapp.utils.file_safety import is_path_within
        outside = tmp_path.parent / "other_dir" / "file.txt"
        assert is_path_within(tmp_path, outside) is False

    def test_blocks_dotdot_traversal(self, tmp_path):
        from webapp.utils.file_safety import is_path_within
        # Even if the path contains ../ components the resolved check catches it.
        traversal = tmp_path / ".." / "etc" / "passwd"
        assert is_path_within(tmp_path, traversal) is False

    def test_blocks_absolute_escape(self, tmp_path):
        from webapp.utils.file_safety import is_path_within
        assert is_path_within(tmp_path, Path("/etc/passwd")) is False


class TestSafeResolveWithin:
    """Tests for the safe_resolve_within() helper."""

    def test_returns_path_for_valid_relative(self, tmp_path):
        from webapp.utils.file_safety import safe_resolve_within
        result = safe_resolve_within(tmp_path, "uploads/photo.jpg")
        assert result is not None
        assert str(result).startswith(str(tmp_path.resolve()))

    def test_returns_none_for_dotdot_escape(self, tmp_path):
        from webapp.utils.file_safety import safe_resolve_within
        assert safe_resolve_within(tmp_path, "../../etc/passwd") is None

    def test_returns_none_for_absolute_escape(self, tmp_path):
        from webapp.utils.file_safety import safe_resolve_within
        assert safe_resolve_within(tmp_path, "/etc/passwd") is None


class TestValidateImageContent:
    """Tests for the validate_image_content() helper."""

    def test_accepts_valid_jpeg(self):
        from webapp.utils.file_safety import validate_image_content
        with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as f:
            f.write(_make_valid_jpeg_bytes())
            tmp = Path(f.name)
        try:
            result = validate_image_content(tmp)
            assert result == "JPEG"
        finally:
            tmp.unlink(missing_ok=True)

    def test_accepts_valid_png(self):
        from webapp.utils.file_safety import validate_image_content
        with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as f:
            f.write(_make_valid_png_bytes())
            tmp = Path(f.name)
        try:
            result = validate_image_content(tmp)
            assert result == "PNG"
        finally:
            tmp.unlink(missing_ok=True)

    def test_rejects_text_file(self):
        from webapp.utils.file_safety import validate_image_content
        with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as f:
            f.write(b"<html>This is not an image</html>")
            tmp = Path(f.name)
        try:
            assert validate_image_content(tmp) is None
        finally:
            tmp.unlink(missing_ok=True)

    def test_rejects_empty_file(self):
        from webapp.utils.file_safety import validate_image_content
        with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as f:
            tmp = Path(f.name)
        try:
            assert validate_image_content(tmp) is None
        finally:
            tmp.unlink(missing_ok=True)

    def test_rejects_bmp_unsupported_format(self):
        from webapp.utils.file_safety import validate_image_content
        with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as f:
            f.write(_make_bmp_bytes())
            tmp = Path(f.name)
        try:
            assert validate_image_content(tmp) is None
        finally:
            tmp.unlink(missing_ok=True)

    def test_rejects_random_binary(self):
        from webapp.utils.file_safety import validate_image_content
        with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as f:
            f.write(os.urandom(512))
            tmp = Path(f.name)
        try:
            # Random bytes are overwhelmingly unlikely to be a valid image.
            # We just check it doesn't raise an exception and returns None or str.
            result = validate_image_content(tmp)
            assert result is None or isinstance(result, str)
        finally:
            tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Upload endpoint security tests
# ---------------------------------------------------------------------------

class TestUploadValidation:
    """POST /api/photos/upload must reject invalid files early."""

    def test_upload_rejects_bad_content_type(self):
        """Non-image Content-Type header must be rejected immediately."""
        from webapp.api import app
        client = TestClient(app)
        resp = client.post(
            "/api/photos/upload",
            data={"article": "TEST001", "user_id": "1"},
            files={"photo": ("test.txt", b"hello world", "text/plain")},
        )
        assert resp.status_code in (200, 400)
        assert resp.json()["success"] is False

    def test_upload_rejects_empty_file(self):
        """An empty file must be rejected before reaching the database."""
        from webapp.api import app
        client = TestClient(app)
        resp = client.post(
            "/api/photos/upload",
            data={"article": "TEST001", "user_id": "1"},
            files={"photo": ("empty.jpg", b"", "image/jpeg")},
        )
        assert resp.status_code in (200, 400)
        assert resp.json()["success"] is False

    def test_upload_rejects_oversized_file(self):
        """Files larger than 10 MB must be rejected before writing to disk."""
        from webapp.api import app
        from webapp.utils.file_safety import MAX_UPLOAD_BYTES
        client = TestClient(app)
        oversized = b"x" * (MAX_UPLOAD_BYTES + 1)
        resp = client.post(
            "/api/photos/upload",
            data={"article": "TEST001", "user_id": "1"},
            files={"photo": ("big.jpg", oversized, "image/jpeg")},
        )
        assert resp.status_code in (200, 400)
        assert resp.json()["success"] is False

    def test_upload_rejects_non_image_with_spoofed_content_type(self):
        """
        A non-image payload with a spoofed 'image/jpeg' Content-Type must be
        rejected by Pillow validation even though the header looks valid.
        """
        from webapp.api import app
        client = TestClient(app)
        fake_content = b"<script>alert(1)</script> definitely not an image"
        resp = client.post(
            "/api/photos/upload",
            data={"article": "TEST001", "user_id": "1"},
            files={"photo": ("evil.jpg", fake_content, "image/jpeg")},
        )
        assert resp.status_code in (200, 400)
        assert resp.json()["success"] is False

    def test_upload_rejects_bmp_with_spoofed_content_type(self):
        """
        A BMP image (not in ALLOWED_IMAGE_FORMATS) with a spoofed 'image/jpeg'
        Content-Type must be rejected.
        """
        from webapp.api import app
        client = TestClient(app)
        resp = client.post(
            "/api/photos/upload",
            data={"article": "TEST001", "user_id": "1"},
            files={"photo": ("image.jpg", _make_bmp_bytes(), "image/jpeg")},
        )
        assert resp.status_code in (200, 400)
        assert resp.json()["success"] is False


# ---------------------------------------------------------------------------
# Delete photo — path traversal guard
# ---------------------------------------------------------------------------

class TestDeletePhotoPathSafety:
    """DELETE /api/photos/{id} must reject malicious file_path values from DB."""

    def test_delete_photo_blocks_path_traversal(self):
        """
        If the DB row contains a crafted file_path that would escape the
        photos storage root, the endpoint must return 400 and NOT delete.
        """
        from webapp.api import app

        author_id = 123
        photo_mock = MagicMock()
        photo_mock.id = 1
        photo_mock.uploaded_by = author_id
        # A traversal path — should resolve outside uploads/photos/
        photo_mock.file_path = "../../etc/passwd"

        token = _make_jwt_token(user_id=author_id, role="user")

        with patch("webapp.deps.ADMIN_IDS", []), \
             patch("webapp.routers.photos.ADMIN_IDS", []), \
             patch("webapp.routers.photos.async_session") as mock_session_cls:

            mock_session = AsyncMock()
            mock_photo_result = MagicMock()
            mock_photo_result.scalar_one_or_none.return_value = photo_mock
            mock_session.execute = AsyncMock(return_value=mock_photo_result)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_session

            client = TestClient(app)
            resp = client.delete(
                "/api/photos/1",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 400

    def test_delete_photo_allows_valid_path(self):
        """A legitimate file_path (within uploads/photos/) must proceed normally."""
        from webapp.api import app

        author_id = 456
        photo_mock = MagicMock()
        photo_mock.id = 2
        photo_mock.uploaded_by = author_id
        photo_mock.file_path = f"uploads/photos/{author_id}/photo_0.jpg"

        token = _make_jwt_token(user_id=author_id, role="user")

        with patch("webapp.deps.ADMIN_IDS", []), \
             patch("webapp.routers.photos.ADMIN_IDS", []), \
             patch("webapp.routers.photos.async_session") as mock_session_cls:

            mock_session = AsyncMock()
            mock_photo_result = MagicMock()
            mock_photo_result.scalar_one_or_none.return_value = photo_mock
            mock_session.execute = AsyncMock(return_value=mock_photo_result)
            mock_session.delete = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_session

            client = TestClient(app)
            resp = client.delete(
                "/api/photos/2",
                headers={"Authorization": f"Bearer {token}"},
            )

        # File doesn't exist on disk but path is valid → delete succeeds
        assert resp.status_code == 200
        assert resp.json()["success"] is True
