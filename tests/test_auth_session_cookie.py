"""Tests for cookie sessions, CSRF double-submit and logout (ADR-0013)."""

from datetime import timedelta
from typing import Any

import pytest
from httpx import AsyncClient

from app.utils.security import create_access_token

CREDS = {"email": "cookie@example.com", "password": "cookiepass123"}  # pragma: allowlist secret


def _set_cookie_headers(response: Any) -> dict[str, str]:
    """Map cookie name -> raw Set-Cookie header."""
    out: dict[str, str] = {}
    for raw in response.headers.get_list("set-cookie"):
        out[raw.split("=", 1)[0]] = raw
    return out


def _attrs(raw: str) -> set[str]:
    return {part.strip().lower() for part in raw.split(";")[1:]}


def _value(raw: str) -> str:
    return raw.split(";")[0].split("=", 1)[1]


@pytest.fixture
def https_client(client: AsyncClient) -> AsyncClient:
    """Client on https so the Secure cookies are stored and replayed."""
    client.base_url = "https://test"  # type: ignore[assignment]
    return client


async def _register(c: AsyncClient) -> Any:
    return await c.post("/api/v1/auth/register", json=CREDS)


async def _login(c: AsyncClient) -> Any:
    return await c.post(
        "/api/v1/auth/login",
        data={"username": CREDS["email"], "password": CREDS["password"]},
    )


class TestCookieFlags:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("flow", ["register", "login"])
    async def test_flags(self, client: AsyncClient, flow: str) -> None:
        resp = await _register(client)
        if flow == "login":
            resp = await _login(client)
        assert resp.status_code in (200, 201)
        assert "access_token" in resp.json()  # body unchanged
        cookies = _set_cookie_headers(resp)

        session = _attrs(cookies["session"])
        assert {"httponly", "secure", "samesite=lax", "path=/api"} <= session
        assert "max-age=86400" in session
        assert _value(cookies["session"]) == resp.json()["access_token"]

        csrf = _attrs(cookies["csrf_token"])
        assert {"secure", "samesite=lax", "path=/"} <= csrf
        assert "httponly" not in csrf
        assert "max-age=86400" in csrf
        assert len(_value(cookies["csrf_token"])) >= 32

    @pytest.mark.asyncio
    async def test_secure_relaxed_in_debug(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.config import settings

        monkeypatch.setattr(settings, "DEBUG", True)
        cookies = _set_cookie_headers(await _register(client))
        assert "secure" not in _attrs(cookies["session"])
        assert "secure" not in _attrs(cookies["csrf_token"])
        assert "httponly" in _attrs(cookies["session"])

    @pytest.mark.asyncio
    async def test_csrf_token_differs_per_login(self, client: AsyncClient) -> None:
        a = _set_cookie_headers(await _register(client))["csrf_token"]
        b = _set_cookie_headers(await _login(client))["csrf_token"]
        assert _value(a) != _value(b)


class TestCookieAuth:
    @pytest.mark.asyncio
    async def test_cookie_only_get_me(self, https_client: AsyncClient) -> None:
        await _register(https_client)
        assert "Authorization" not in https_client.headers
        resp = await https_client.get("/api/v1/auth/me/")
        assert resp.status_code == 200
        assert resp.json()["email"] == CREDS["email"]

    @pytest.mark.asyncio
    async def test_unsafe_without_csrf_header_is_403_and_deletes_nothing(
        self, https_client: AsyncClient
    ) -> None:
        await _register(https_client)
        csrf = {"X-CSRF-Token": https_client.cookies["csrf_token"]}
        movie = await https_client.post(
            "/api/v1/movies/", json={"title": "M", "year": 2024}, headers=csrf
        )
        assert movie.status_code == 201
        rk = await https_client.post(
            "/api/v1/rankings/",
            json={"movie_id": movie.json()["id"], "rating": 5},
            headers=csrf,
        )
        assert rk.status_code == 201

        resp = await https_client.delete("/api/v1/rankings/all/")
        assert resp.status_code == 403
        assert resp.json() == {"detail": "CSRF token missing or invalid"}
        listing = await https_client.get("/api/v1/rankings/")
        assert len(listing.json()["items"]) == 1

    @pytest.mark.asyncio
    async def test_wrong_csrf_header_is_403(self, https_client: AsyncClient) -> None:
        await _register(https_client)
        resp = await https_client.delete(
            "/api/v1/rankings/all/", headers={"X-CSRF-Token": "not-the-token"}
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_missing_csrf_cookie_is_403(self, https_client: AsyncClient) -> None:
        await _register(https_client)
        https_client.cookies.delete("csrf_token")
        resp = await https_client.delete(
            "/api/v1/rankings/all/", headers={"X-CSRF-Token": "anything"}
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_matching_csrf_header_allows_delete(self, https_client: AsyncClient) -> None:
        await _register(https_client)
        resp = await https_client.delete(
            "/api/v1/rankings/all/",
            headers={"X-CSRF-Token": https_client.cookies["csrf_token"]},
        )
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_safe_method_needs_no_csrf(self, https_client: AsyncClient) -> None:
        await _register(https_client)
        assert (await https_client.get("/api/v1/rankings/")).status_code == 200


class TestBearerCompatibility:
    @pytest.mark.asyncio
    async def test_bearer_needs_no_csrf(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.delete("/api/v1/rankings/all/", headers=auth_headers)
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_bearer_header_skips_csrf_even_with_cookie_jar(
        self, https_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        # The test_user fixture registered on this client, so the jar holds cookies.
        resp = await https_client.delete("/api/v1/rankings/all/", headers=auth_headers)
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_no_credentials_is_401(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/auth/me/")
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Could not validate credentials"

    @pytest.mark.asyncio
    async def test_invalid_bearer_is_401(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/auth/me/", headers={"Authorization": "Bearer garbage"})
        assert resp.status_code == 401


class TestInvalidCookie:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("method", ["GET", "DELETE"])
    async def test_garbage_cookie_is_401(self, client: AsyncClient, method: str) -> None:
        url = "/api/v1/auth/me/" if method == "GET" else "/api/v1/rankings/all/"
        client.cookies.set("session", "garbage")
        client.cookies.set("csrf_token", "x")
        resp = await client.request(method, url, headers={"X-CSRF-Token": "x"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.parametrize("method", ["GET", "DELETE"])
    async def test_expired_cookie_is_401_even_without_csrf(
        self, client: AsyncClient, method: str
    ) -> None:
        expired = create_access_token({"sub": "x"}, expires_delta=timedelta(seconds=-60))
        client.cookies.set("session", expired)
        url = "/api/v1/auth/me/" if method == "GET" else "/api/v1/rankings/all/"
        resp = await client.request(method, url)
        assert resp.status_code == 401


class TestLogout:
    @pytest.mark.asyncio
    async def test_logout_clears_cookies_and_session(self, https_client: AsyncClient) -> None:
        await _register(https_client)
        assert (await https_client.get("/api/v1/auth/me/")).status_code == 200

        resp = await https_client.post("/api/v1/auth/logout/")
        assert resp.status_code == 204
        cookies = _set_cookie_headers(resp)
        for name, path in (("session", "path=/api"), ("csrf_token", "path=/")):
            attrs = _attrs(cookies[name])
            assert "max-age=0" in attrs
            assert path in attrs
            assert _value(cookies[name]) in ("", '""')

        assert (await https_client.get("/api/v1/auth/me/")).status_code == 401

    @pytest.mark.asyncio
    async def test_logout_without_auth_is_204(self, client: AsyncClient) -> None:
        assert (await client.post("/api/v1/auth/logout/")).status_code == 204
