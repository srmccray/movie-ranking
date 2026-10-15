"""Tests for Amazon Prime import: updating a movie's TMDB match.

NOTE: All URLs must include trailing slashes.
"""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from tests.import_amazon_helpers import create_mock_tmdb_result, create_test_csv


class TestUpdateMovieMatch:
    """Tests for PATCH /api/v1/import/amazon-prime/session/{session_id}/movie/{index}/match/ endpoint."""

    @pytest.mark.asyncio
    async def test_update_match_success(self, client: AsyncClient, auth_headers: dict):
        """Test updating a movie's TMDB match."""
        csv_file = create_test_csv([{"Type": "Movie", "Title": "Test Movie"}])

        with patch("app.routers.import_amazon.TMDBService") as mock_tmdb_class:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.search_movies.return_value = [
                create_mock_tmdb_result(
                    tmdb_id=100,
                    title="Wrong Movie",
                    year=2024,
                    poster_url="https://image.tmdb.org/t/p/w185/wrong.jpg",
                    overview="Wrong overview",
                ),
                create_mock_tmdb_result(tmdb_id=101, title="Alt 1", year=2024),
            ]
            mock_tmdb_class.return_value = mock_instance

            upload_response = await client.post(
                "/api/v1/import/amazon-prime/upload/",
                files={"file": ("test.csv", csv_file, "text/csv")},
                headers=auth_headers,
            )

        session_id = upload_response.json()["session_id"]

        # Verify initial match
        initial_movies = upload_response.json()["movies"]
        assert len(initial_movies) == 1
        assert initial_movies[0]["tmdb_match"]["tmdb_id"] == 100
        assert len(initial_movies[0]["alternatives"]) == 1

        # Update to a different match
        response = await client.patch(
            f"/api/v1/import/amazon-prime/session/{session_id}/movie/0/match/",
            json={
                "tmdb_id": 999,
                "title": "Correct Movie",
                "year": 2023,
                "poster_url": "https://image.tmdb.org/t/p/w185/correct.jpg",
                "overview": "The correct movie overview",
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify updated match
        assert data["tmdb_match"]["tmdb_id"] == 999
        assert data["tmdb_match"]["title"] == "Correct Movie"
        assert data["tmdb_match"]["year"] == 2023
        assert data["tmdb_match"]["poster_url"] == "https://image.tmdb.org/t/p/w185/correct.jpg"
        assert data["tmdb_match"]["overview"] == "The correct movie overview"
        assert data["confidence"] == 1.0  # User-selected
        assert data["alternatives"] == []  # Cleared
        assert data["status"] == "pending"  # Still pending

    @pytest.mark.asyncio
    async def test_update_match_on_unmatched_movie(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test updating match on a previously unmatched movie."""
        csv_file = create_test_csv([{"Type": "Movie", "Title": "Unknown Movie"}])

        with patch("app.routers.import_amazon.TMDBService") as mock_tmdb_class:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            # No match found initially
            mock_instance.search_movies.return_value = []
            mock_tmdb_class.return_value = mock_instance

            upload_response = await client.post(
                "/api/v1/import/amazon-prime/upload/",
                files={"file": ("test.csv", csv_file, "text/csv")},
                headers=auth_headers,
            )

        session_id = upload_response.json()["session_id"]

        # Verify no initial match
        initial_movies = upload_response.json()["movies"]
        assert initial_movies[0]["tmdb_match"] is None
        assert initial_movies[0]["confidence"] == 0.0

        # User manually selects a match
        response = await client.patch(
            f"/api/v1/import/amazon-prime/session/{session_id}/movie/0/match/",
            json={
                "tmdb_id": 12345,
                "title": "Found Movie",
                "year": 2020,
                "poster_url": None,
                "overview": None,
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["tmdb_match"]["tmdb_id"] == 12345
        assert data["tmdb_match"]["title"] == "Found Movie"
        assert data["confidence"] == 1.0
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_update_match_session_persists(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that updating match persists in session."""
        csv_file = create_test_csv([{"Type": "Movie", "Title": "Test Movie"}])

        with patch("app.routers.import_amazon.TMDBService") as mock_tmdb_class:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.search_movies.return_value = [
                create_mock_tmdb_result(tmdb_id=100, title="Original", year=2024)
            ]
            mock_tmdb_class.return_value = mock_instance

            upload_response = await client.post(
                "/api/v1/import/amazon-prime/upload/",
                files={"file": ("test.csv", csv_file, "text/csv")},
                headers=auth_headers,
            )

        session_id = upload_response.json()["session_id"]

        # Update match
        await client.patch(
            f"/api/v1/import/amazon-prime/session/{session_id}/movie/0/match/",
            json={
                "tmdb_id": 555,
                "title": "New Match",
                "year": 2022,
                "poster_url": None,
                "overview": None,
            },
            headers=auth_headers,
        )

        # Get session and verify change persisted
        session_response = await client.get(
            f"/api/v1/import/amazon-prime/session/{session_id}/",
            headers=auth_headers,
        )

        assert session_response.status_code == 200
        movies = session_response.json()["movies"]
        assert movies[0]["tmdb_match"]["tmdb_id"] == 555
        assert movies[0]["tmdb_match"]["title"] == "New Match"
        assert movies[0]["confidence"] == 1.0

    @pytest.mark.asyncio
    async def test_update_match_then_add_movie(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test updating match then adding the movie works correctly."""
        csv_file = create_test_csv([{"Type": "Movie", "Title": "Test Movie"}])

        with patch("app.routers.import_amazon.TMDBService") as mock_tmdb_class:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.search_movies.return_value = [
                create_mock_tmdb_result(tmdb_id=100, title="Wrong", year=2024)
            ]
            mock_tmdb_class.return_value = mock_instance

            upload_response = await client.post(
                "/api/v1/import/amazon-prime/upload/",
                files={"file": ("test.csv", csv_file, "text/csv")},
                headers=auth_headers,
            )

        session_id = upload_response.json()["session_id"]

        # Update match to correct movie
        await client.patch(
            f"/api/v1/import/amazon-prime/session/{session_id}/movie/0/match/",
            json={
                "tmdb_id": 77777,
                "title": "Correct Movie",
                "year": 2021,
                "poster_url": "https://image.tmdb.org/t/p/w185/correct.jpg",
                "overview": "The correct one",
            },
            headers=auth_headers,
        )

        # Add the movie with the updated match
        add_response = await client.post(
            f"/api/v1/import/amazon-prime/session/{session_id}/movie/0/add/",
            json={"rating": 5},
            headers=auth_headers,
        )

        assert add_response.status_code == 201
        data = add_response.json()
        assert data["rating"] == 5

        # Verify the correct movie was added to rankings
        rankings_response = await client.get(
            "/api/v1/rankings/",
            headers=auth_headers,
        )
        rankings = rankings_response.json()["items"]
        assert len(rankings) == 1
        assert rankings[0]["movie"]["title"] == "Correct Movie"

    @pytest.mark.asyncio
    async def test_update_match_invalid_session_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test updating match with invalid session returns 404."""
        response = await client.patch(
            "/api/v1/import/amazon-prime/session/invalid-session/movie/0/match/",
            json={
                "tmdb_id": 123,
                "title": "Test",
                "year": 2024,
                "poster_url": None,
                "overview": None,
            },
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_match_invalid_index_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test updating match with invalid index returns 404."""
        csv_file = create_test_csv([{"Type": "Movie", "Title": "Test Movie"}])

        with patch("app.routers.import_amazon.TMDBService") as mock_tmdb_class:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.search_movies.return_value = [
                create_mock_tmdb_result(tmdb_id=1, title="Test", year=2024)
            ]
            mock_tmdb_class.return_value = mock_instance

            upload_response = await client.post(
                "/api/v1/import/amazon-prime/upload/",
                files={"file": ("test.csv", csv_file, "text/csv")},
                headers=auth_headers,
            )

        session_id = upload_response.json()["session_id"]

        response = await client.patch(
            f"/api/v1/import/amazon-prime/session/{session_id}/movie/999/match/",
            json={
                "tmdb_id": 123,
                "title": "Test",
                "year": 2024,
                "poster_url": None,
                "overview": None,
            },
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "index" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_match_without_auth_returns_401(self, client: AsyncClient):
        """Test updating match without auth returns 401."""
        response = await client.patch(
            "/api/v1/import/amazon-prime/session/some-session/movie/0/match/",
            json={
                "tmdb_id": 123,
                "title": "Test",
                "year": 2024,
                "poster_url": None,
                "overview": None,
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_match_missing_required_fields_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test updating match with missing required fields returns 422."""
        csv_file = create_test_csv([{"Type": "Movie", "Title": "Test Movie"}])

        with patch("app.routers.import_amazon.TMDBService") as mock_tmdb_class:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.search_movies.return_value = [
                create_mock_tmdb_result(tmdb_id=1, title="Test", year=2024)
            ]
            mock_tmdb_class.return_value = mock_instance

            upload_response = await client.post(
                "/api/v1/import/amazon-prime/upload/",
                files={"file": ("test.csv", csv_file, "text/csv")},
                headers=auth_headers,
            )

        session_id = upload_response.json()["session_id"]

        # Missing tmdb_id and title
        response = await client.patch(
            f"/api/v1/import/amazon-prime/session/{session_id}/movie/0/match/",
            json={"year": 2024},
            headers=auth_headers,
        )

        assert response.status_code == 422
