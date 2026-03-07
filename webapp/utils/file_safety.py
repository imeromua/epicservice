"""Centralized file safety utilities for upload validation and path handling.

Provides helpers for:
- Enforcing maximum upload size before writing to disk.
- Validating actual image content with Pillow (not just Content-Type).
- Checking that resolved filesystem paths stay within expected storage roots
  to prevent path traversal vulnerabilities.
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Maximum permitted upload size for image files (10 MB).
# Callers should read at most MAX_UPLOAD_BYTES + 1 bytes and reject if the
# returned buffer is longer than MAX_UPLOAD_BYTES.
MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024  # 10 MB

# Pillow format names that are accepted for photo uploads.
# Everything is re-saved as JPEG by compress_image(), so this list acts as an
# input filter rather than a storage-format constraint.
ALLOWED_IMAGE_FORMATS = frozenset({"JPEG", "PNG", "WEBP", "GIF"})


def is_path_within(root: Path, candidate: Path) -> bool:
    """Return True iff the resolved *candidate* path is inside *root*.

    Both paths are resolved (symlinks expanded, ``..`` collapsed) before the
    comparison so that crafted relative components cannot escape the root.

    Args:
        root: The directory that must contain ``candidate``.
        candidate: The path to validate.

    Returns:
        True if ``candidate`` resolves to a location inside ``root``,
        False otherwise (including on any OS error).
    """
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False


def safe_resolve_within(root: Path, relative_path: str) -> Optional[Path]:
    """Resolve *relative_path* under *root* and return it only if still inside.

    Useful when building file paths from DB-stored relative values: the
    function returns ``None`` (and logs a warning) if the resolved result
    would escape ``root``.

    Args:
        root: Expected storage root directory.
        relative_path: Relative path component, potentially attacker-controlled.

    Returns:
        Resolved absolute ``Path`` if safe, ``None`` if it would escape root.
    """
    try:
        root_resolved = root.resolve()
        candidate = (root_resolved / relative_path).resolve()
        candidate.relative_to(root_resolved)
        return candidate
    except (ValueError, OSError):
        logger.warning(
            "Path traversal blocked: root=%s relative=%s", root, relative_path
        )
        return None


def validate_image_content(file_path: Path) -> Optional[str]:
    """Validate that *file_path* is a real, supported image.

    Opens the file with Pillow to detect its actual format — this check is
    independent of the file extension or the ``Content-Type`` header supplied
    by the client.  Then forces a full decode (``img.load()``) to catch
    truncated or otherwise corrupt data.

    Args:
        file_path: Path to the file to validate.

    Returns:
        The Pillow format name (e.g. ``'JPEG'``, ``'PNG'``) if the file is a
        valid supported image, or ``None`` if validation fails for any reason.
    """
    try:
        from PIL import Image  # noqa: PLC0415

        with Image.open(file_path) as img:
            fmt = img.format
            if fmt not in ALLOWED_IMAGE_FORMATS:
                logger.warning(
                    "Rejected unsupported image format: %s (path=%s)", fmt, file_path
                )
                return None
            # Force full decode to reject truncated / corrupted files.
            img.load()
        return fmt
    except Exception as e:  # UnidentifiedImageError, OSError, etc.
        logger.warning("Image validation failed for %s: %s", file_path, e)
        return None
