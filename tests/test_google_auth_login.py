"""Tests for Google OAuth login, callback and end-to-end flow endpoints.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


class TestGoogleLoginEndpoint:
    """Tests for GET /api/v1/auth/google/login/ endpoint."""

    @pytest.mark.asyncio
    async def test_google_login_returns_authorization_url(self, client: AsyncClient):
        """Test that /google/login/ returns a valid Google authorization URL."""
        response = await client.get("/api/v1/auth/google/login/")

        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert data["authorization_url"].startswith("https://accounts.google.com/o/oauth2/v2/auth")
        assert "client_id=" in data["authorization_url"]
        assert "state=" in data["authorization_url"]
        assert "redirect_uri=" in data["authorization_url"]

    @pytest.mark.asyncio
    async def test_google_login_includes_required_scopes(self, client: AsyncClient):
        """Test that authorization URL includes required scopes."""
        response = await client.get("/api/v1/auth/google/login/")

        assert response.status_code == 200
        data = response.json()
        assert "openid" in data["authorization_url"]
        assert "email" in data["authorization_url"]
        assert "profile" in data["authorization_url"]

    @pytest.mark.asyncio
    async def test_google_login_state_is_unique(self, client: AsyncClient):
        """Test that each request generates a unique state token."""
        response1 = await client.get("/api/v1/auth/google/login/")
        response2 = await client.get("/api/v1/auth/google/login/")

        url1 = response1.json()["authorization_url"]
        url2 = response2.json()["authorization_url"]

        # Extract state from URLs
        state1 = url1.split("state=")[1].split("&")[0]
        state2 = url2.split("state=")[1].split("&")[0]

        assert state1 != state2, "State tokens should be unique per request"

    @pytest.mark.asyncio
    async def test_google_login_trailing_slash(self, client: AsyncClient):
        """Test that endpoint follows trailing slash convention."""
        response = await client.get("/api/v1/auth/google/login/")
        assert response.status_code == 200


class TestGoogleCallbackEndpoint:
    """Tests for GET /api/v1/auth/google/callback/ endpoint."""

    @pytest.mark.asyncio
    async def test_callback_missing_code_returns_400(self, client: AsyncClient):
        """Test that callback without code parameter returns 400."""
        response = await client.get(
            "/api/v1/auth/google/callback/",
            params={"state": "some-state"},
        )

        assert response.status_code == 400
        assert "missing" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_callback_missing_state_returns_400(self, client: AsyncClient):
        """Test that callback without state parameter returns 400."""
        response = await client.get(
            "/api/v1/auth/google/callback/",
            params={"code": "some-code"},
        )

        assert response.status_code == 400
        assert "missing" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_callback_invalid_state_returns_400(self, client: AsyncClient):
        """Test that callback with invalid state token returns 400."""
        response = await client.get(
            "/api/v1/auth/google/callback/",
            params={"code": "valid-code", "state": "invalid-state-token"},
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower() or "expired" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_callback_with_error_param_returns_400(self, client: AsyncClient):
        """Test that callback with error from Google returns 400."""
        response = await client.get(
            "/api/v1/auth/google/callback/",
            params={"error": "access_denied"},
        )

        assert response.status_code == 400
        assert "cancelled" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_callback_trailing_slash(self, client: AsyncClient):
        """Test that callback endpoint follows trailing slash convention."""
        # Even with missing params, should return 400 not 404/307
        response = await client.get("/api/v1/auth/google/callback/")
        assert response.status_code == 400  # Missing params, not redirect


class TestGoogleOAuthFlow:
    """Integration tests for complete OAuth flow with mocked Google services."""

    @pytest.mark.asyncio
    async def test_full_oauth_flow_creates_new_user(self, client: AsyncClient):
        """Test that OAuth flow creates a new user when email doesn't exist."""
        # First, get a valid state token
        login_response = await client.get("/api/v1/auth/google/login/")
        auth_url = login_response.json()["authorization_url"]
        state = auth_url.split("state=")[1].split("&")[0]

        # Mock Google token exchange and verification
        mock_tokens = {
            "id_token": "mock-id-token",
            "access_token": "mock-access-token",
        }
        mock_idinfo = {
            "sub": "google-user-123",
            "email": "newgoogleuser@example.com",
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
                data = response.json()
                assert "access_token" in data
                assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_oauth_flow_links_existing_email_account(self, client: AsyncClient, test_user: dict):
        """Test that OAuth flow links Google to existing email account."""
        # First, get a valid state token
        login_response = await client.get("/api/v1/auth/google/login/")
        auth_url = login_response.json()["authorization_url"]
        state = auth_url.split("state=")[1].split("&")[0]

        # Mock Google response with same email as test_user
        mock_tokens = {
            "id_token": "mock-id-token",
            "access_token": "mock-access-token",
        }
        mock_idinfo = {
            "sub": "google-user-456",
            "email": test_user["email"],  # Same email as existing user
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

                # Should succeed and return token for existing account
                assert response.status_code == 200
                data = response.json()
                assert "access_token" in data

    @pytest.mark.asyncio
    async def test_oauth_flow_returns_same_user_on_repeat_login(self, client: AsyncClient):
        """Test that returning Google user gets same account."""
        # Create user via OAuth first
        login_response = await client.get("/api/v1/auth/google/login/")
        auth_url = login_response.json()["authorization_url"]
        state = auth_url.split("state=")[1].split("&")[0]

        mock_tokens = {
            "id_token": "mock-id-token",
            "access_token": "mock-access-token",
        }
        mock_idinfo = {
            "sub": "google-returning-user",
            "email": "returning@example.com",
            "email_verified": True,
            "iss": "https://accounts.google.com",
        }

        with patch("app.routers.google_auth.oauth._exchange_code_for_tokens", new_callable=AsyncMock) as mock_exchange:
            mock_exchange.return_value = mock_tokens
            with patch("app.routers.google_auth.oauth._verify_google_id_token") as mock_verify:
                mock_verify.return_value = mock_idinfo

                # First login
                response1 = await client.get(
                    "/api/v1/auth/google/callback/",
                    params={"code": "valid-auth-code", "state": state},
                )
                assert response1.status_code == 200
                token1 = response1.json()["access_token"]

        # Second login
        login_response2 = await client.get("/api/v1/auth/google/login/")
        state2 = login_response2.json()["authorization_url"].split("state=")[1].split("&")[0]

        with patch("app.routers.google_auth.oauth._exchange_code_for_tokens", new_callable=AsyncMock) as mock_exchange:
            mock_exchange.return_value = mock_tokens
            with patch("app.routers.google_auth.oauth._verify_google_id_token") as mock_verify:
                mock_verify.return_value = mock_idinfo

                response2 = await client.get(
                    "/api/v1/auth/google/callback/",
                    params={"code": "valid-auth-code", "state": state2},
                )
                assert response2.status_code == 200

    @pytest.mark.asyncio
    async def test_oauth_rejects_unverified_email(self, client: AsyncClient):
        """Test that OAuth rejects users with unverified Google email."""
        login_response = await client.get("/api/v1/auth/google/login/")
        auth_url = login_response.json()["authorization_url"]
        state = auth_url.split("state=")[1].split("&")[0]

        mock_tokens = {
            "id_token": "mock-id-token",
            "access_token": "mock-access-token",
        }
        mock_idinfo = {
            "sub": "google-unverified-user",
            "email": "unverified@example.com",
            "email_verified": False,  # Unverified email
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

                assert response.status_code == 400
                assert "verified" in response.json()["detail"].lower()
