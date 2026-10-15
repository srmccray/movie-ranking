"""Google callback sets the session cookies and gates the legacy ?token= redirect."""

from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.config import settings

CALLBACK = "/api/v1/auth/google/callback/"
LOGIN = "/api/v1/auth/google/login/"
IDINFO = {
    "sub": "google-cookie-user",
    "email": "cookieuser@example.com",
    "email_verified": True,
    "iss": "https://accounts.google.com",
}


@contextmanager
def google_mocks():
    with patch(
        "app.routers.google_auth.oauth._exchange_code_for_tokens",
        new_callable=AsyncMock,
        return_value={"id_token": "x", "access_token": "y"},
    ), patch(
        "app.routers.google_auth.oauth._verify_google_id_token",
        return_value=IDINFO,
    ):
        yield


async def _state(client: AsyncClient, redirect_uri: str | None) -> str:
    params = {"redirect_uri": redirect_uri} if redirect_uri else None
    resp = await client.get(LOGIN, params=params)
    assert resp.status_code == 200
    return resp.json()["authorization_url"].split("state=")[1].split("&")[0]


async def _callback(client: AsyncClient, redirect_uri: str | None):
    state = await _state(client, redirect_uri)
    with google_mocks():
        return await client.get(
            CALLBACK,
            params={"code": "c", "state": state},
            follow_redirects=False,
        )


def _cookie_headers(resp) -> dict[str, str]:
    """Map cookie name -> full Set-Cookie header."""
    out = {}
    for raw in resp.headers.get_list("set-cookie"):
        out[raw.split("=", 1)[0]] = raw
    return out


def _assert_cookies(resp) -> str:
    """Check cookie flags and return the session cookie value (the JWT)."""
    cookies = _cookie_headers(resp)
    assert set(cookies) == {"session", "csrf_token"}
    session = cookies["session"].lower()
    assert "httponly" in session
    assert "secure" in session
    assert "samesite=lax" in session
    assert "path=/api" in session
    csrf = cookies["csrf_token"].lower()
    assert "httponly" not in csrf
    assert "secure" in csrf
    assert "samesite=lax" in csrf
    assert "path=/;" in csrf or csrf.endswith("path=/")
    return cookies["session"].split("=", 1)[1].split(";", 1)[0]


class TestRedirectSetsCookies:
    @pytest.mark.asyncio
    async def test_redirect_sets_both_cookies_legacy_default(self, client: AsyncClient):
        resp = await _callback(client, "/auth/google/callback")
        assert resp.status_code == 302
        jwt = _assert_cookies(resp)
        # Default flag is true: legacy token still in the URL, same value as cookie.
        assert resp.headers["location"] == f"/auth/google/callback?token={jwt}"

    @pytest.mark.asyncio
    async def test_flag_off_location_has_no_token(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(settings, "GOOGLE_LEGACY_TOKEN_IN_URL", False)
        resp = await _callback(client, "/auth/google/callback")
        assert resp.status_code == 302
        jwt = _assert_cookies(resp)
        location = resp.headers["location"]
        assert location == "/auth/google/callback"
        assert "token" not in location
        assert jwt not in location
        assert jwt not in resp.text

    @pytest.mark.asyncio
    async def test_flag_off_session_cookie_value_is_valid_jwt(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(settings, "GOOGLE_LEGACY_TOKEN_IN_URL", False)
        resp = await _callback(client, "/settings")
        jwt = _assert_cookies(resp)
        me = await client.get(
            "/api/v1/auth/me/", headers={"Authorization": f"Bearer {jwt}"}
        )
        assert me.status_code == 200
        assert me.json()["email"] == IDINFO["email"]

    @pytest.mark.asyncio
    async def test_cookies_not_secure_in_debug(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(settings, "DEBUG", True)
        resp = await _callback(client, "/settings")
        for raw in _cookie_headers(resp).values():
            assert "secure" not in raw.lower()


class TestJsonPathSetsCookies:
    @pytest.mark.asyncio
    async def test_no_redirect_uri_returns_token_json_and_cookies(
        self, client: AsyncClient
    ):
        resp = await _callback(client, None)
        assert resp.status_code == 200
        body = resp.json()
        assert body["token_type"] == "bearer"
        assert _assert_cookies(resp) == body["access_token"]

    @pytest.mark.asyncio
    async def test_json_unchanged_when_flag_off(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(settings, "GOOGLE_LEGACY_TOKEN_IN_URL", False)
        resp = await _callback(client, None)
        assert resp.status_code == 200
        assert set(resp.json()) == {"access_token", "token_type"}
        _assert_cookies(resp)


class TestRejectedRedirectUri:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "value", ["https://evil.example/", "//evil.example", "javascript:alert(1)"]
    )
    @pytest.mark.parametrize("flag", [True, False])
    async def test_login_rejects_and_sets_no_cookies(
        self,
        client: AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
        value: str,
        flag: bool,
    ):
        monkeypatch.setattr(settings, "GOOGLE_LEGACY_TOKEN_IN_URL", flag)
        resp = await client.get(LOGIN, params={"redirect_uri": value})
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid redirect_uri"
        assert not resp.headers.get_list("set-cookie")
