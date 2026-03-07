"""
webapp/utils/download_tokens.py

Short-lived one-time download tokens for Telegram Mini App (TMA) file downloads.

In Telegram Mini Apps the embedded WebView blocks programmatic blob downloads
(anchor.click() with the `download` attribute does not trigger a save dialog).
The workaround is to:
  1. Issue a short-lived one-time token tied to a specific download URL.
  2. Return the token to the frontend.
  3. Frontend opens `download_url?dl_token=<token>` via Telegram.WebApp.openLink()
     which launches the user's external browser where normal downloads work.

Tokens are stored in-process memory (thread-safe dict) with a 60-second TTL.
They are consumed on first use (one-time).
"""

import secrets
import threading
import time
from typing import Any, Dict

from fastapi import HTTPException

_tokens: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()

# How long a token remains valid (seconds).
_TOKEN_TTL_SECONDS = 60


def _cleanup_expired() -> None:
    """Remove all expired tokens.  Must be called while holding ``_lock``."""
    now = time.time()
    expired = [k for k, v in _tokens.items() if now > v["expires_at"]]
    for k in expired:
        del _tokens[k]


def create_download_token(user_id: int, resource_url: str, role: str = "user") -> str:
    """
    Create and store a short-lived one-time download token.

    Args:
        user_id:      Telegram user ID of the authenticated requester.
        resource_url: The exact URL path this token authorises, e.g.
                      ``/api/archives/download-all/123``.
                      The download endpoint will reject any token whose
                      ``resource_url`` does not match the requested path.
        role:         One of ``"user"``, ``"moderator"``, or ``"admin"``.
                      Download endpoints use this to perform the same
                      permission check as they would with a live TMA header.

    Returns:
        A 43-character URL-safe random token string.
    """
    token = secrets.token_urlsafe(32)
    expires_at = time.time() + _TOKEN_TTL_SECONDS
    with _lock:
        _cleanup_expired()
        _tokens[token] = {
            "user_id": user_id,
            "resource_url": resource_url,
            "role": role,
            "expires_at": expires_at,
        }
    return token


def validate_and_consume_token(token: str, resource_url: str) -> Dict[str, Any]:
    """
    Validate a one-time download token and consume it (remove it from the store).

    Args:
        token:        The token string received from the ``dl_token`` query param.
        resource_url: The URL path that is being requested.  Must match the value
                      stored in the token.

    Returns:
        The token data dict with keys ``user_id``, ``role``, ``resource_url``.

    Raises:
        HTTPException 401: if the token is missing, expired, or the
                           ``resource_url`` does not match.
    """
    with _lock:
        _cleanup_expired()
        data = _tokens.get(token)
        if data is None:
            raise HTTPException(
                status_code=401, detail="Invalid or expired download token"
            )
        if data["resource_url"] != resource_url:
            raise HTTPException(
                status_code=401, detail="Download token resource mismatch"
            )
        if time.time() > data["expires_at"]:
            del _tokens[token]
            raise HTTPException(
                status_code=401, detail="Download token has expired"
            )
        # One-time use: consume the token.
        del _tokens[token]
        return dict(data)
