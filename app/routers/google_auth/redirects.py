"""Validation of post-OAuth redirect targets (open-redirect protection)."""

import os
from urllib.parse import urlsplit

from fastapi import HTTPException, status

from app.config import settings

_DEV_ORIGINS = ("http://localhost:3000",)
_DEBUG_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")
_DEFAULT_PORTS = {"http": 80, "https": 443}


def _origin_of(value: str) -> str | None:
    """Return a normalized ``scheme://host[:port]`` for an absolute URL, or None."""
    try:
        parts = urlsplit(value.strip())
        port = parts.port
    except ValueError:
        return None
    if parts.scheme not in _DEFAULT_PORTS or not parts.hostname:
        return None
    if parts.username is not None or parts.password is not None:
        return None
    origin = f"{parts.scheme}://{parts.hostname.lower()}"
    if port is not None and port != _DEFAULT_PORTS[parts.scheme]:
        origin += f":{port}"
    return origin


def allowed_origins() -> set[str]:
    """Build the allowlist of origins a redirect_uri may point at."""
    candidates = list(_DEV_ORIGINS)
    if os.environ.get("CORS_ORIGIN"):
        candidates.append(os.environ["CORS_ORIGIN"])
    if settings.DEBUG:
        candidates.extend(_DEBUG_ORIGINS)
    return {o for o in (_origin_of(c) for c in candidates) if o}


def is_valid_redirect_uri(value: str | None) -> bool:
    """Return True if value is None, a safe relative path, or an allowlisted URL."""
    if value is None:
        return True
    if not value or any(ord(c) < 0x20 or ord(c) == 0x7F for c in value):
        return False
    if "\\" in value or value != value.strip():
        return False
    if value.startswith("/"):
        return not value.startswith("//")
    origin = _origin_of(value)
    return origin is not None and origin in allowed_origins()


def validate_redirect_uri(value: str | None) -> str | None:
    """Return value unchanged if acceptable, otherwise raise HTTP 400."""
    if not is_valid_redirect_uri(value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid redirect_uri",
        )
    return value
