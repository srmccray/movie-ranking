"""Tests for Google OAuth password behavior, profile and account linking endpoints.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


class TestGoogleUserCanStillUsePassword:
    """Tests verifying linked accounts can use password login."""

    @pytest.mark.asyncio
    async def test_linked_user_can_login_with_password(self, client: AsyncClient, test_user: dict):
        """Test that user who linked Google can still use password login."""
        # Link Google to existing account
        login_response = await client.get("/api/v1/auth/google/login/")
        auth_url = login_response.json()["authorization_url"]
        state = auth_url.split("state=")[1].split("&")[0]

        mock_tokens = {"id_token": "mock-id-token", "access_token": "mock-access-token"}
        mock_idinfo = {
            "sub": "google-link-user",
            "email": test_user["email"],
            "email_verified": True,
            "iss": "https://accounts.google.com",
        }

        with patch("app.routers.google_auth.oauth._exchange_code_for_tokens", new_callable=AsyncMock) as mock_exchange:
            mock_exchange.return_value = mock_tokens
            with patch("app.routers.google_auth.oauth._verify_google_id_token") as mock_verify:
                mock_verify.return_value = mock_idinfo

                response = await client.get(
                    "/api/v1/auth/google/callback/",
                    params={"code": "valid-auth-code", "state": state},
                )
                assert response.status_code == 200

        # Now test password login still works
        password_login = await client.post(
            "/api/v1/auth/login",
            data={"username": test_user["email"], "password": test_user["password"]},
        )

        assert password_login.status_code == 200
        assert "access_token" in password_login.json()


class TestGoogleOnlyUserCannotUsePassword:
    """Tests for Google-only users (no password)."""

    @pytest.mark.asyncio
    async def test_google_only_user_cannot_password_login(self, client: AsyncClient):
        """Test that Google-only user cannot login with password."""
        # Create user via Google OAuth
        login_response = await client.get("/api/v1/auth/google/login/")
        auth_url = login_response.json()["authorization_url"]
        state = auth_url.split("state=")[1].split("&")[0]

        mock_tokens = {"id_token": "mock-id-token", "access_token": "mock-access-token"}
        mock_idinfo = {
            "sub": "google-only-user-123",
            "email": "googleonly@example.com",
            "email_verified": True,
            "iss": "https://accounts.google.com",
        }

        with patch("app.routers.google_auth.oauth._exchange_code_for_tokens", new_callable=AsyncMock) as mock_exchange:
            mock_exchange.return_value = mock_tokens
            with patch("app.routers.google_auth.oauth._verify_google_id_token") as mock_verify:
                mock_verify.return_value = mock_idinfo

                response = await client.get(
                    "/api/v1/auth/google/callback/",
                    params={"code": "valid-auth-code", "state": state},
                )
                assert response.status_code == 200

        # Try password login with this Google-only user
        password_login = await client.post(
            "/api/v1/auth/login",
            data={"username": "googleonly@example.com", "password": "anypassword123"},
        )

        # Should fail because user has no password
        assert password_login.status_code == 401


class TestUserProfileEndpoint:
    """Tests for GET /api/v1/auth/me/ endpoint."""

    @pytest.mark.asyncio
    async def test_get_profile_returns_user_info(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that /me/ returns current user profile."""
        response = await client.get("/api/v1/auth/me/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert data["email"] == "test@example.com"
        assert "auth_provider" in data
        assert data["auth_provider"] == "local"
        assert "has_google_linked" in data
        assert data["has_google_linked"] is False
        assert "has_password" in data
        assert data["has_password"] is True
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_profile_without_auth_returns_401(self, client: AsyncClient):
        """Test that /me/ without auth returns 401."""
        response = await client.get("/api/v1/auth/me/")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_profile_trailing_slash(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that endpoint follows trailing slash convention."""
        response = await client.get("/api/v1/auth/me/", headers=auth_headers)
        assert response.status_code == 200


class TestGoogleLinkEndpoint:
    """Tests for GET /api/v1/auth/google/link/ endpoint."""

    @pytest.mark.asyncio
    async def test_google_link_returns_authorization_url(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that /google/link/ returns a valid Google authorization URL."""
        response = await client.get(
            "/api/v1/auth/google/link/",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert data["authorization_url"].startswith(
            "https://accounts.google.com/o/oauth2/v2/auth"
        )
        assert "client_id=" in data["authorization_url"]
        assert "state=" in data["authorization_url"]

    @pytest.mark.asyncio
    async def test_google_link_without_auth_returns_401(self, client: AsyncClient):
        """Test that /google/link/ without auth returns 401."""
        response = await client.get("/api/v1/auth/google/link/")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_google_link_already_linked_returns_409(
        self, client: AsyncClient, test_user: dict
    ):
        """Test that /google/link/ returns 409 if already linked."""
        auth_headers = {"Authorization": f"Bearer {test_user['access_token']}"}

        # First, link Google via the login flow (simulates existing linked account)
        login_response = await client.get("/api/v1/auth/google/login/")
        auth_url = login_response.json()["authorization_url"]
        state = auth_url.split("state=")[1].split("&")[0]

        mock_tokens = {
            "id_token": "mock-id-token",
            "access_token": "mock-access-token",
        }
        mock_idinfo = {
            "sub": "google-link-test-409",
            "email": test_user["email"],
            "email_verified": True,
            "iss": "https://accounts.google.com",
        }

        with patch(
            "app.routers.google_auth.oauth._exchange_code_for_tokens", new_callable=AsyncMock
        ) as mock_exchange:
            mock_exchange.return_value = mock_tokens
            with patch("app.routers.google_auth.oauth._verify_google_id_token") as mock_verify:
                mock_verify.return_value = mock_idinfo

                await client.get(
                    "/api/v1/auth/google/callback/",
                    params={"code": "valid-auth-code", "state": state},
                )

        # Now try to initiate linking - should fail
        link_response = await client.get(
            "/api/v1/auth/google/link/",
            headers=auth_headers,
        )

        assert link_response.status_code == 409
        assert "already linked" in link_response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_google_link_trailing_slash(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that endpoint follows trailing slash convention."""
        response = await client.get("/api/v1/auth/google/link/", headers=auth_headers)
        assert response.status_code == 200


class TestGoogleLinkCallbackEndpoint:
    """Tests for GET /api/v1/auth/google/link/callback/ endpoint."""

    @pytest.mark.asyncio
    async def test_link_callback_missing_code_redirects_with_error(
        self, client: AsyncClient
    ):
        """Test that callback without code redirects with error."""
        response = await client.get(
            "/api/v1/auth/google/link/callback/",
            params={"state": "some-state"},
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "error=invalid_request" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_link_callback_invalid_state_redirects_with_error(
        self, client: AsyncClient
    ):
        """Test that callback with invalid state redirects with error."""
        response = await client.get(
            "/api/v1/auth/google/link/callback/",
            params={"code": "valid-code", "state": "invalid-state-token"},
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "error=invalid_state" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_link_callback_with_user_cancellation_redirects(
        self, client: AsyncClient
    ):
        """Test that callback with error from Google redirects appropriately."""
        response = await client.get(
            "/api/v1/auth/google/link/callback/",
            params={"error": "access_denied"},
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "error=cancelled" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_full_link_flow_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test complete account linking flow."""
        # Initiate linking
        link_response = await client.get(
            "/api/v1/auth/google/link/",
            headers=auth_headers,
        )
        assert link_response.status_code == 200

        auth_url = link_response.json()["authorization_url"]
        state = auth_url.split("state=")[1].split("&")[0]
        # The callback is a browser navigation: it carries the session cookie
        client.cookies.set("session", auth_headers["Authorization"].split(" ", 1)[1])

        # Mock Google response
        mock_tokens = {
            "id_token": "mock-id-token",
            "access_token": "mock-access-token",
        }
        mock_idinfo = {
            "sub": "google-link-flow-123",
            "email": "different@google.com",  # Different email is OK
            "email_verified": True,
            "iss": "https://accounts.google.com",
        }

        with patch(
            "app.routers.google_auth.oauth._exchange_code_for_tokens", new_callable=AsyncMock
        ) as mock_exchange:
            mock_exchange.return_value = mock_tokens
            with patch("app.routers.google_auth.oauth._verify_google_id_token") as mock_verify:
                mock_verify.return_value = mock_idinfo

                # Complete the link callback
                callback_response = await client.get(
                    "/api/v1/auth/google/link/callback/",
                    params={"code": "valid-auth-code", "state": state},
                    follow_redirects=False,
                )

                assert callback_response.status_code == 302
                assert "linked=success" in callback_response.headers["location"]

        # Verify the user now has Google linked
        profile_response = await client.get("/api/v1/auth/me/", headers=auth_headers)
        assert profile_response.status_code == 200
        profile = profile_response.json()
        assert profile["has_google_linked"] is True
        assert profile["auth_provider"] == "linked"

    @pytest.mark.asyncio
    async def test_link_callback_rejects_already_linked_google(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that linking fails if Google account is linked to another user."""
        # Create a second user and link a Google account to them
        register_response = await client.post(
            "/api/v1/auth/register",
            json={"email": "other@example.com", "password": "password123"},
        )
        other_token = register_response.json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}

        # Link Google to the other user first
        other_link_response = await client.get(
            "/api/v1/auth/google/link/",
            headers=other_headers,
        )
        other_state = other_link_response.json()["authorization_url"].split("state=")[1].split("&")[0]
        # The callback is a browser navigation: it carries the session cookie
        client.cookies.set("session", other_token)

        mock_tokens = {
            "id_token": "mock-id-token",
            "access_token": "mock-access-token",
        }
        mock_idinfo = {
            "sub": "shared-google-id-456",  # Same Google ID we'll try to use later
            "email": "shared@google.com",
            "email_verified": True,
            "iss": "https://accounts.google.com",
        }

        with patch(
            "app.routers.google_auth.oauth._exchange_code_for_tokens", new_callable=AsyncMock
        ) as mock_exchange:
            mock_exchange.return_value = mock_tokens
            with patch("app.routers.google_auth.oauth._verify_google_id_token") as mock_verify:
                mock_verify.return_value = mock_idinfo

                # Link to other user
                await client.get(
                    "/api/v1/auth/google/link/callback/",
                    params={"code": "valid-auth-code", "state": other_state},
                    follow_redirects=False,
                )

        # Now try to link the same Google account to the original test user
        link_response = await client.get(
            "/api/v1/auth/google/link/",
            headers=auth_headers,
        )
        state = link_response.json()["authorization_url"].split("state=")[1].split("&")[0]
        # The callback is a browser navigation: it carries the session cookie
        client.cookies.set("session", auth_headers["Authorization"].split(" ", 1)[1])

        with patch(
            "app.routers.google_auth.oauth._exchange_code_for_tokens", new_callable=AsyncMock
        ) as mock_exchange:
            mock_exchange.return_value = mock_tokens
            with patch("app.routers.google_auth.oauth._verify_google_id_token") as mock_verify:
                mock_verify.return_value = mock_idinfo  # Same Google ID

                callback_response = await client.get(
                    "/api/v1/auth/google/link/callback/",
                    params={"code": "valid-auth-code", "state": state},
                    follow_redirects=False,
                )

                assert callback_response.status_code == 302
                assert "error=already_linked_other" in callback_response.headers["location"]

    @pytest.mark.asyncio
    async def test_link_callback_trailing_slash(self, client: AsyncClient):
        """Test that endpoint follows trailing slash convention."""
        response = await client.get(
            "/api/v1/auth/google/link/callback/",
            params={"error": "test"},
            follow_redirects=False,
        )
        assert response.status_code == 302  # Redirects, not 404/307
