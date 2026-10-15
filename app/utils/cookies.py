"""Session and CSRF cookie helpers (ADR-0013)."""

import secrets

from fastapi import Response

from app.config import settings

SESSION_COOKIE = "session"
CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "X-CSRF-Token"
SESSION_PATH = "/api"
CSRF_PATH = "/"


def set_session_cookies(response: Response, token: str) -> None:
    """Set the httpOnly session cookie and the readable CSRF cookie."""
    max_age = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    secure = not settings.DEBUG
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=max_age,
        path=SESSION_PATH,
        httponly=True,
        secure=secure,
        samesite="lax",
    )
    response.set_cookie(
        CSRF_COOKIE,
        secrets.token_urlsafe(32),
        max_age=max_age,
        path=CSRF_PATH,
        httponly=False,
        secure=secure,
        samesite="lax",
    )


def clear_session_cookies(response: Response) -> None:
    """Expire both cookies, using the same attributes they were set with."""
    secure = not settings.DEBUG
    response.delete_cookie(
        SESSION_COOKIE, path=SESSION_PATH, httponly=True, secure=secure, samesite="lax"
    )
    response.delete_cookie(
        CSRF_COOKIE, path=CSRF_PATH, httponly=False, secure=secure, samesite="lax"
    )
