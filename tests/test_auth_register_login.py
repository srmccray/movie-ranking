"""Tests for authentication registration and login endpoints.

These tests verify:
- User registration with correct JSON format
- User login with correct form-urlencoded format (the bug that was fixed)
- Invalid credentials handling
"""

import pytest
from httpx import AsyncClient


class TestRegisterEndpoint:
    """Tests for POST /api/v1/auth/register endpoint."""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        """Test successful user registration with valid credentials."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepassword123",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["access_token"] is not None
        assert len(data["access_token"]) > 0

    @pytest.mark.asyncio
    async def test_register_returns_valid_jwt(self, client: AsyncClient):
        """Test that registration returns a valid JWT token format."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "jwttest@example.com",
                "password": "securepassword123",
            },
        )

        assert response.status_code == 201
        data = response.json()
        token = data["access_token"]
        # JWT tokens have 3 parts separated by dots
        parts = token.split(".")
        assert len(parts) == 3, "JWT should have 3 parts (header.payload.signature)"

    @pytest.mark.asyncio
    async def test_register_duplicate_email_returns_409(
        self, client: AsyncClient, test_user: dict
    ):
        """Test that registering with an existing email returns 409 Conflict."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user["email"],  # Using existing test user email
                "password": "anotherpassword123",
            },
        )

        assert response.status_code == 409
        data = response.json()
        assert "detail" in data
        assert "already registered" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_invalid_email_returns_422(self, client: AsyncClient):
        """Test that invalid email format returns 422 validation error."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "securepassword123",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_short_password_returns_422(self, client: AsyncClient):
        """Test that password shorter than 8 characters returns 422."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "shortpwd@example.com",
                "password": "short",  # Less than 8 characters
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_missing_email_returns_422(self, client: AsyncClient):
        """Test that missing email field returns 422."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "password": "securepassword123",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_missing_password_returns_422(self, client: AsyncClient):
        """Test that missing password field returns 422."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "nopwd@example.com",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_with_json_content_type(self, client: AsyncClient):
        """Test that registration correctly uses application/json Content-Type."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "contenttype@example.com",
                "password": "securepassword123",
            },
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 201


class TestLoginEndpoint:
    """Tests for POST /api/v1/auth/login endpoint.

    CRITICAL: These tests verify the Content-Type bug fix.
    The login endpoint uses OAuth2PasswordRequestForm which requires
    application/x-www-form-urlencoded, NOT application/json.
    """

    @pytest.mark.asyncio
    async def test_login_success_with_form_data(
        self, client: AsyncClient, test_user: dict
    ):
        """Test successful login with form-urlencoded data.

        This is the critical test for the Content-Type bug fix.
        The login endpoint MUST receive form-urlencoded data, not JSON.
        """
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user["email"],
                "password": test_user["password"],
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["access_token"] is not None

    @pytest.mark.asyncio
    async def test_login_form_data_without_explicit_content_type(
        self, client: AsyncClient, test_user: dict
    ):
        """Test login works when sending form data (httpx auto-sets Content-Type)."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user["email"],
                "password": test_user["password"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    @pytest.mark.asyncio
    async def test_login_returns_valid_jwt(
        self, client: AsyncClient, test_user: dict
    ):
        """Test that login returns a valid JWT token format."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user["email"],
                "password": test_user["password"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        token = data["access_token"]
        # JWT tokens have 3 parts separated by dots
        parts = token.split(".")
        assert len(parts) == 3

    @pytest.mark.asyncio
    async def test_login_invalid_password_returns_401(
        self, client: AsyncClient, test_user: dict
    ):
        """Test that wrong password returns 401 Unauthorized."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user["email"],
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_login_nonexistent_user_returns_401(self, client: AsyncClient):
        """Test that login with non-existent user returns 401."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "somepassword123",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_missing_username_returns_422(self, client: AsyncClient):
        """Test that missing username field returns 422."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "password": "somepassword",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_missing_password_returns_422(
        self, client: AsyncClient, test_user: dict
    ):
        """Test that missing password field returns 422."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user["email"],
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_with_json_body_fails(
        self, client: AsyncClient, test_user: dict
    ):
        """Test that login with JSON body fails (requires form-urlencoded).

        This verifies the Content-Type requirement - login MUST use form data.
        If someone sends JSON, it should fail because OAuth2PasswordRequestForm
        expects form-urlencoded data.
        """
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user["email"],
                "password": test_user["password"],
            },
        )

        # Should fail because login expects form data, not JSON
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_case_insensitive_email(
        self, client: AsyncClient, test_user: dict
    ):
        """Test login behavior with different email casing.

        Note: This test documents current behavior. If emails should be
        case-insensitive, the backend should normalize them.
        """
        # Using uppercase email - this tests current behavior
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user["email"].upper(),
                "password": test_user["password"],
            },
        )

        # Current implementation is case-sensitive, so this fails
        # If case-insensitive login is desired, this test should be updated
        assert response.status_code == 401
