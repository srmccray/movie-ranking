"""Tests for protected endpoints and end-to-end authentication flows.

These tests verify:
- Protected endpoint access
- Trailing-slash behavior of auth routes
- Full authentication flow: register -> login -> access protected endpoint
- Token validation
"""

import pytest
from httpx import AsyncClient


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
        password = "journeypassword123"  # pragma: allowlist secret

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
