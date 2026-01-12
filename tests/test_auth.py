"""Tests for authentication endpoints.

These tests verify the authentication flow including:
- User registration with correct JSON format
- User login with correct form-urlencoded format (the bug that was fixed)
- Invalid credentials handling
- Protected endpoint access
- Full authentication flow: register -> login -> access protected endpoint
"""

import pytest
from httpx import AsyncClient

from app.utils.security import get_password_hash


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


class TestProtectedEndpoints:
    """Tests for protected endpoints requiring authentication."""

    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token_returns_401(
        self, client: AsyncClient
    ):
        """Test that accessing protected endpoint without token returns 401."""
        response = await client.post(
            "/api/v1/movies/",
            json={
                "title": "Test Movie",
                "year": 2024,
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_valid_token_succeeds(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that protected endpoint works with valid token."""
        response = await client.post(
            "/api/v1/movies/",
            json={
                "title": "Test Movie",
                "year": 2024,
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Movie"

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_invalid_token_returns_401(
        self, client: AsyncClient
    ):
        """Test that invalid token returns 401."""
        response = await client.post(
            "/api/v1/movies/",
            json={
                "title": "Test Movie",
            },
            headers={"Authorization": "Bearer invalidtoken"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_malformed_auth_header(
        self, client: AsyncClient
    ):
        """Test that malformed Authorization header returns 401."""
        response = await client.post(
            "/api/v1/movies/",
            json={"title": "Test Movie"},
            headers={"Authorization": "NotBearer sometoken"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_rankings_endpoint_requires_auth(self, client: AsyncClient):
        """Test that rankings endpoint requires authentication."""
        response = await client.get("/api/v1/rankings/")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_rankings_endpoint_with_valid_token(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that rankings endpoint works with valid token."""
        response = await client.get(
            "/api/v1/rankings/",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data


class TestTrailingSlashes:
    """Tests for trailing slash handling on endpoints.

    These tests verify the trailing slash bug fix.
    FastAPI endpoints are defined with trailing slashes, so requests
    without trailing slashes should either work or redirect properly.
    """

    @pytest.mark.asyncio
    async def test_movies_endpoint_with_trailing_slash(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that POST /movies/ works with trailing slash."""
        response = await client.post(
            "/api/v1/movies/",
            json={"title": "Slash Test Movie", "year": 2024},
            headers=auth_headers,
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_rankings_endpoint_with_trailing_slash(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that GET /rankings/ works with trailing slash."""
        response = await client.get(
            "/api/v1/rankings/",
            headers=auth_headers,
        )

        assert response.status_code == 200


class TestFullAuthenticationFlow:
    """Integration tests for complete authentication flows."""

    @pytest.mark.asyncio
    async def test_register_then_access_protected_endpoint(
        self, client: AsyncClient
    ):
        """Test flow: Register -> Use token to access protected endpoint."""
        # Step 1: Register a new user
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "flowtest@example.com",
                "password": "flowpassword123",
            },
        )

        assert register_response.status_code == 201
        token = register_response.json()["access_token"]

        # Step 2: Use token to access protected endpoint
        movies_response = await client.post(
            "/api/v1/movies/",
            json={"title": "Flow Test Movie", "year": 2024},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert movies_response.status_code == 201
        assert movies_response.json()["title"] == "Flow Test Movie"

    @pytest.mark.asyncio
    async def test_register_login_access_protected_endpoint(
        self, client: AsyncClient
    ):
        """Test complete flow: Register -> Login -> Access protected endpoint.

        This is the critical integration test that verifies the entire
        authentication flow works correctly, especially the login Content-Type fix.
        """
        email = "fullflow@example.com"
        password = "fullflowpassword123"

        # Step 1: Register
        register_response = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password},
        )
        assert register_response.status_code == 201

        # Step 2: Login (using form-urlencoded as required)
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert login_response.status_code == 200
        login_token = login_response.json()["access_token"]

        # Step 3: Access protected endpoint with login token
        movies_response = await client.post(
            "/api/v1/movies/",
            json={"title": "Full Flow Movie", "year": 2024},
            headers={"Authorization": f"Bearer {login_token}"},
        )
        assert movies_response.status_code == 201

        # Step 4: Access rankings (also protected)
        rankings_response = await client.get(
            "/api/v1/rankings/",
            headers={"Authorization": f"Bearer {login_token}"},
        )
        assert rankings_response.status_code == 200

    @pytest.mark.asyncio
    async def test_register_login_create_ranking_flow(
        self, client: AsyncClient
    ):
        """Test complete user journey: Register -> Login -> Create Movie -> Rank it."""
        email = "journey@example.com"
        password = "journeypassword123"

        # Register
        register_response = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password},
        )
        assert register_response.status_code == 201
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create a movie
        movie_response = await client.post(
            "/api/v1/movies/",
            json={"title": "Journey Movie", "year": 2024},
            headers=headers,
        )
        assert movie_response.status_code == 201
        movie_id = movie_response.json()["id"]

        # Rank the movie
        ranking_response = await client.post(
            "/api/v1/rankings/",
            json={"movie_id": movie_id, "rating": 5},
            headers=headers,
        )
        assert ranking_response.status_code == 201
        assert ranking_response.json()["rating"] == 5

        # Verify ranking appears in list
        rankings_response = await client.get(
            "/api/v1/rankings/",
            headers=headers,
        )
        assert rankings_response.status_code == 200
        items = rankings_response.json()["items"]
        assert len(items) == 1
        assert items[0]["movie"]["title"] == "Journey Movie"
        assert items[0]["rating"] == 5


class TestTokenValidation:
    """Tests for JWT token validation."""

    @pytest.mark.asyncio
    async def test_token_can_be_used_multiple_times(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that the same token can be used for multiple requests."""
        # First request
        response1 = await client.get(
            "/api/v1/rankings/",
            headers=auth_headers,
        )
        assert response1.status_code == 200

        # Second request with same token
        response2 = await client.get(
            "/api/v1/rankings/",
            headers=auth_headers,
        )
        assert response2.status_code == 200

    @pytest.mark.asyncio
    async def test_different_users_get_different_tokens(self, client: AsyncClient):
        """Test that different users receive different tokens."""
        # Register first user
        response1 = await client.post(
            "/api/v1/auth/register",
            json={"email": "user1@example.com", "password": "password123"},
        )
        token1 = response1.json()["access_token"]

        # Register second user
        response2 = await client.post(
            "/api/v1/auth/register",
            json={"email": "user2@example.com", "password": "password123"},
        )
        token2 = response2.json()["access_token"]

        assert token1 != token2
