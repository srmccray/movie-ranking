"""Tests for rankings endpoints.

These tests verify the rankings functionality including:
- Creating rankings with rated_at
- Listing rankings
- Deleting rankings (including the trailing slash fix)
"""

import pytest
from httpx import AsyncClient


class TestCreateRanking:
    """Tests for POST /api/v1/rankings/ endpoint."""

    @pytest.mark.asyncio
    async def test_create_ranking_success(
        self, client: AsyncClient, auth_headers: dict, test_movie: dict
    ):
        """Test successful ranking creation."""
        response = await client.post(
            "/api/v1/rankings/",
            json={
                "movie_id": test_movie["movie_id"],
                "rating": 5,
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["rating"] == 5
        assert data["movie_id"] == test_movie["movie_id"]
        assert "rated_at" in data

    @pytest.mark.asyncio
    async def test_create_ranking_with_custom_rated_at(
        self, client: AsyncClient, auth_headers: dict, test_movie: dict
    ):
        """Test creating ranking with custom rated_at date."""
        custom_date = "2025-12-25T10:00:00Z"
        response = await client.post(
            "/api/v1/rankings/",
            json={
                "movie_id": test_movie["movie_id"],
                "rating": 4,
                "rated_at": custom_date,
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["rated_at"].startswith("2025-12-25")

    @pytest.mark.asyncio
    async def test_create_ranking_defaults_rated_at(
        self, client: AsyncClient, auth_headers: dict, test_movie: dict
    ):
        """Test that rated_at defaults to current time when not provided."""
        response = await client.post(
            "/api/v1/rankings/",
            json={
                "movie_id": test_movie["movie_id"],
                "rating": 3,
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert "rated_at" in data
        assert data["rated_at"] is not None

    @pytest.mark.asyncio
    async def test_update_ranking_preserves_rated_at(
        self, client: AsyncClient, auth_headers: dict, test_movie: dict
    ):
        """Test that updating rating without rated_at preserves original date."""
        # Create initial ranking with custom date
        custom_date = "2025-06-15T10:00:00Z"
        await client.post(
            "/api/v1/rankings/",
            json={
                "movie_id": test_movie["movie_id"],
                "rating": 3,
                "rated_at": custom_date,
            },
            headers=auth_headers,
        )

        # Update rating without specifying rated_at
        response = await client.post(
            "/api/v1/rankings/",
            json={
                "movie_id": test_movie["movie_id"],
                "rating": 5,
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["rating"] == 5
        # rated_at should still be the original date
        assert data["rated_at"].startswith("2025-06-15")


class TestListRankings:
    """Tests for GET /api/v1/rankings/ endpoint."""

    @pytest.mark.asyncio
    async def test_list_rankings_empty(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test listing rankings when none exist."""
        response = await client.get(
            "/api/v1/rankings/",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_rankings_with_items(
        self, client: AsyncClient, auth_headers: dict, test_movie: dict
    ):
        """Test listing rankings with items."""
        # Create a ranking first
        await client.post(
            "/api/v1/rankings/",
            json={
                "movie_id": test_movie["movie_id"],
                "rating": 4,
            },
            headers=auth_headers,
        )

        response = await client.get(
            "/api/v1/rankings/",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["total"] == 1
        assert data["items"][0]["rating"] == 4
        assert "rated_at" in data["items"][0]


class TestDeleteRanking:
    """Tests for DELETE /api/v1/rankings/{ranking_id}/ endpoint.

    These tests specifically verify the trailing slash fix that was implemented
    to prevent 404 errors when deleting rankings.
    """

    @pytest.mark.asyncio
    async def test_delete_ranking_success(
        self, client: AsyncClient, auth_headers: dict, test_movie: dict
    ):
        """Test successful ranking deletion with trailing slash."""
        # Create a ranking
        create_response = await client.post(
            "/api/v1/rankings/",
            json={
                "movie_id": test_movie["movie_id"],
                "rating": 5,
            },
            headers=auth_headers,
        )
        ranking_id = create_response.json()["id"]

        # Delete the ranking (with trailing slash)
        delete_response = await client.delete(
            f"/api/v1/rankings/{ranking_id}/",
            headers=auth_headers,
        )

        assert delete_response.status_code == 204

        # Verify it's deleted
        list_response = await client.get(
            "/api/v1/rankings/",
            headers=auth_headers,
        )
        assert list_response.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_delete_ranking_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test deleting a non-existent ranking returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.delete(
            f"/api/v1/rankings/{fake_id}/",
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Ranking not found"

    @pytest.mark.asyncio
    async def test_delete_ranking_unauthorized(
        self, client: AsyncClient, test_movie: dict
    ):
        """Test deleting without auth returns 401."""
        # First create a user and ranking
        register_response = await client.post(
            "/api/v1/auth/register",
            json={"email": "user1@test.com", "password": "password123"},
        )
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create movie
        movie_response = await client.post(
            "/api/v1/movies/",
            json={"title": "Test Movie", "year": 2024},
            headers=headers,
        )
        movie_id = movie_response.json()["id"]

        # Create ranking
        ranking_response = await client.post(
            "/api/v1/rankings/",
            json={"movie_id": movie_id, "rating": 5},
            headers=headers,
        )
        ranking_id = ranking_response.json()["id"]

        # Try to delete without auth
        response = await client.delete(
            f"/api/v1/rankings/{ranking_id}/",
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_other_user_ranking_forbidden(
        self, client: AsyncClient
    ):
        """Test deleting another user's ranking returns 403."""
        # Create first user and ranking
        user1_response = await client.post(
            "/api/v1/auth/register",
            json={"email": "user1@example.com", "password": "password123"},
        )
        user1_token = user1_response.json()["access_token"]
        user1_headers = {"Authorization": f"Bearer {user1_token}"}

        movie_response = await client.post(
            "/api/v1/movies/",
            json={"title": "User1 Movie", "year": 2024},
            headers=user1_headers,
        )
        movie_id = movie_response.json()["id"]

        ranking_response = await client.post(
            "/api/v1/rankings/",
            json={"movie_id": movie_id, "rating": 5},
            headers=user1_headers,
        )
        ranking_id = ranking_response.json()["id"]

        # Create second user
        user2_response = await client.post(
            "/api/v1/auth/register",
            json={"email": "user2@example.com", "password": "password123"},
        )
        user2_token = user2_response.json()["access_token"]
        user2_headers = {"Authorization": f"Bearer {user2_token}"}

        # Try to delete user1's ranking as user2
        response = await client.delete(
            f"/api/v1/rankings/{ranking_id}/",
            headers=user2_headers,
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Not authorized to delete this ranking"

    @pytest.mark.asyncio
    async def test_delete_ranking_removes_from_list(
        self, client: AsyncClient, auth_headers: dict, test_movie: dict
    ):
        """Test that deleted ranking is removed from list."""
        # Create two movies and rankings
        movie2_response = await client.post(
            "/api/v1/movies/",
            json={"title": "Second Movie", "year": 2023},
            headers=auth_headers,
        )
        movie2_id = movie2_response.json()["id"]

        # Create rankings for both movies
        ranking1_response = await client.post(
            "/api/v1/rankings/",
            json={"movie_id": test_movie["movie_id"], "rating": 5},
            headers=auth_headers,
        )
        ranking1_id = ranking1_response.json()["id"]

        await client.post(
            "/api/v1/rankings/",
            json={"movie_id": movie2_id, "rating": 4},
            headers=auth_headers,
        )

        # Verify we have 2 rankings
        list_response = await client.get(
            "/api/v1/rankings/",
            headers=auth_headers,
        )
        assert list_response.json()["total"] == 2

        # Delete the first ranking
        delete_response = await client.delete(
            f"/api/v1/rankings/{ranking1_id}/",
            headers=auth_headers,
        )
        assert delete_response.status_code == 204

        # Verify we now have 1 ranking
        list_response = await client.get(
            "/api/v1/rankings/",
            headers=auth_headers,
        )
        assert list_response.json()["total"] == 1
        assert list_response.json()["items"][0]["movie"]["title"] == "Second Movie"
