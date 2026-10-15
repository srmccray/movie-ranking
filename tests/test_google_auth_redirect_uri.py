"""Tests for redirect_uri allowlist validation on Google login/link initiation."""

from unittest.mock import patch

import pytest
from httpx import AsyncClient

ORIGIN = "https://movies.example.com"

REJECTED = [
    "https://evil.example/",
    "//evil.example",
    "//evil.example/path",
    "/\\evil.example",
    "https://movies.example.com.evil.net/",
    "https://movies.example.com@evil.net/",
    "https://evil.net/https://movies.example.com",
    "http://movies.example.com/",  # scheme mismatch
    "https://movies.example.com:8443/",  # port mismatch
    "javascript:alert(1)",
    "data:text/html,hi",
    "/ok\r\nLocation: https://evil.example",
    "relative/path",
    "",
]

ACCEPTED = [
    "/auth/google/callback",
    "/settings",
    f"{ORIGIN}/auth/google/callback",
    f"{ORIGIN}/settings",
    "http://localhost:3000/auth/google/callback",
]


@pytest.fixture(autouse=True)
def cors_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGIN", ORIGIN)


class TestLoginRedirectUri:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("value", REJECTED)
    async def test_rejected_and_no_state_stored(self, client: AsyncClient, value: str):
        with patch(
            "app.routers.google_auth.oauth._create_state_token"
        ) as create_state:
            response = await client.get(
                "/api/v1/auth/google/login/", params={"redirect_uri": value}
            )
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid redirect_uri"
        create_state.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("value", ACCEPTED)
    async def test_accepted(self, client: AsyncClient, value: str):
        response = await client.get(
            "/api/v1/auth/google/login/", params={"redirect_uri": value}
        )
        assert response.status_code == 200
        assert "authorization_url" in response.json()


class TestLinkRedirectUri:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("value", REJECTED)
    async def test_rejected(
        self, client: AsyncClient, auth_headers: dict[str, str], value: str
    ):
        with patch(
            "app.routers.google_auth.oauth._create_state_token"
        ) as create_state:
            response = await client.get(
                "/api/v1/auth/google/link/",
                params={"redirect_uri": value},
                headers=auth_headers,
            )
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid redirect_uri"
        create_state.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("value", ACCEPTED)
    async def test_accepted(
        self, client: AsyncClient, auth_headers: dict[str, str], value: str
    ):
        response = await client.get(
            "/api/v1/auth/google/link/",
            params={"redirect_uri": value},
            headers=auth_headers,
        )
        assert response.status_code == 200
