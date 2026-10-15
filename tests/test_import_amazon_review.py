"""Tests for Amazon Prime import: adding and skipping movies.

NOTE: All URLs must include trailing slashes.
"""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from tests.import_amazon_helpers import create_mock_tmdb_result, create_test_csv


class TestAddMovie:
    """Tests for POST /api/v1/import/amazon-prime/session/{session_id}/movie/{index}/add/ endpoint."""

    @pytest.mark.asyncio
    async def test_add_movie_creates_ranking(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test adding a movie creates a ranking."""
        # Create session
        csv_file = create_test_csv(
            [
                {"Type": "Movie", "Title": "Test Movie", "Date Watched": "2024-01-15"},
            ]
        )

        with patch("app.routers.import_amazon.matching.TMDBService") as mock_tmdb_class:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.search_movies.return_value = [
                create_mock_tmdb_result(
                    tmdb_id=12345, title="Test Movie", year=2024, poster_url=None, overview=None
                )
            ]
            mock_tmdb_class.return_value = mock_instance

            upload_response = await client.post(
                "/api/v1/import/amazon-prime/upload/",
                files={"file": ("test.csv", csv_file, "text/csv")},
                headers=auth_headers,
            )

        session_id = upload_response.json()["session_id"]

        # Add the movie
        response = await client.post(
            f"/api/v1/import/amazon-prime/session/{session_id}/movie/0/add/",
            json={"rating": 4},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["rating"] == 4
        assert "rated_at" in data
        assert "id" in data

    @pytest.mark.asyncio
    async def test_add_movie_with_custom_rated_at(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test adding a movie with custom rated_at."""
        csv_file = create_test_csv(
            [
                {"Type": "Movie", "Title": "Test Movie"},
            ]
        )

        with patch("app.routers.import_amazon.matching.TMDBService") as mock_tmdb_class:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.search_movies.return_value = [
                create_mock_tmdb_result(
                    tmdb_id=99999, title="Test Movie", year=2024, poster_url=None, overview=None
                )
            ]
            mock_tmdb_class.return_value = mock_instance

            upload_response = await client.post(
                "/api/v1/import/amazon-prime/upload/",
                files={"file": ("test.csv", csv_file, "text/csv")},
                headers=auth_headers,
            )

        session_id = upload_response.json()["session_id"]

        custom_date = "2023-06-15T10:00:00Z"
        response = await client.post(
            f"/api/v1/import/amazon-prime/session/{session_id}/movie/0/add/",
            json={"rating": 5, "rated_at": custom_date},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["rating"] == 5
        # Note: rated_at is stored as naive UTC, so exact comparison needs care
        assert data["rated_at"].startswith("2023-06-15")

    @pytest.mark.asyncio
    async def test_add_movie_invalid_rating_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test adding movie with invalid rating returns 422."""
        csv_file = create_test_csv([{"Type": "Movie", "Title": "Test"}])

        with patch("app.routers.import_amazon.matching.TMDBService") as mock_tmdb_class:
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

        response = await client.post(
            f"/api/v1/import/amazon-prime/session/{session_id}/movie/0/add/",
            json={"rating": 10},  # Invalid: must be 1-5
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_add_movie_rating_zero_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test adding movie with zero rating returns 422."""
        csv_file = create_test_csv([{"Type": "Movie", "Title": "Test"}])

        with patch("app.routers.import_amazon.matching.TMDBService") as mock_tmdb_class:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.search_movies.return_value = [
                create_mock_tmdb_result(tmdb_id=2, title="Test", year=2024)
            ]
            mock_tmdb_class.return_value = mock_instance

            upload_response = await client.post(
                "/api/v1/import/amazon-prime/upload/",
                files={"file": ("test.csv", csv_file, "text/csv")},
                headers=auth_headers,
            )

        session_id = upload_response.json()["session_id"]

        response = await client.post(
            f"/api/v1/import/amazon-prime/session/{session_id}/movie/0/add/",
            json={"rating": 0},  # Invalid: must be 1-5
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_add_already_processed_movie_returns_400(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test adding already-processed movie returns 400."""
        csv_file = create_test_csv([{"Type": "Movie", "Title": "Test"}])

        with patch("app.routers.import_amazon.matching.TMDBService") as mock_tmdb_class:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.search_movies.return_value = [
                create_mock_tmdb_result(tmdb_id=88888, title="Test", year=2024)
            ]
            mock_tmdb_class.return_value = mock_instance

            upload_response = await client.post(
                "/api/v1/import/amazon-prime/upload/",
                files={"file": ("test.csv", csv_file, "text/csv")},
                headers=auth_headers,
            )

        session_id = upload_response.json()["session_id"]

        # Add once
        await client.post(
            f"/api/v1/import/amazon-prime/session/{session_id}/movie/0/add/",
            json={"rating": 4},
            headers=auth_headers,
        )

        # Try to add again
        response = await client.post(
            f"/api/v1/import/amazon-prime/session/{session_id}/movie/0/add/",
            json={"rating": 5},
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "already been processed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_add_movie_invalid_index_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test adding movie with invalid index returns 404."""
        csv_file = create_test_csv([{"Type": "Movie", "Title": "Test"}])

        with patch("app.routers.import_amazon.matching.TMDBService") as mock_tmdb_class:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.search_movies.return_value = [
                create_mock_tmdb_result(tmdb_id=3, title="Test", year=2024)
            ]
            mock_tmdb_class.return_value = mock_instance

            upload_response = await client.post(
                "/api/v1/import/amazon-prime/upload/",
                files={"file": ("test.csv", csv_file, "text/csv")},
                headers=auth_headers,
            )

        session_id = upload_response.json()["session_id"]

        response = await client.post(
            f"/api/v1/import/amazon-prime/session/{session_id}/movie/999/add/",
            json={"rating": 4},
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "index" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_add_movie_invalid_session_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test adding movie with invalid session returns 404."""
        response = await client.post(
            "/api/v1/import/amazon-prime/session/invalid-session/movie/0/add/",
            json={"rating": 4},
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_add_movie_without_auth_returns_401(self, client: AsyncClient):
        """Test adding movie without auth returns 401."""
        response = await client.post(
            "/api/v1/import/amazon-prime/session/some-session/movie/0/add/",
            json={"rating": 4},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_add_movie_without_tmdb_match_returns_400(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test adding a movie without TMDB match returns 400."""
        csv_file = create_test_csv([{"Type": "Movie", "Title": "Unknown Movie"}])

        with patch("app.routers.import_amazon.matching.TMDBService") as mock_tmdb_class:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            # Return empty list - no TMDB match found
            mock_instance.search_movies.return_value = []
            mock_tmdb_class.return_value = mock_instance

            upload_response = await client.post(
                "/api/v1/import/amazon-prime/upload/",
                files={"file": ("test.csv", csv_file, "text/csv")},
                headers=auth_headers,
            )

        session_id = upload_response.json()["session_id"]

        # Try to add movie without TMDB match
        response = await client.post(
            f"/api/v1/import/amazon-prime/session/{session_id}/movie/0/add/",
            json={"rating": 4},
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "TMDB match" in response.json()["detail"]


class TestSkipMovie:
    """Tests for POST /api/v1/import/amazon-prime/session/{session_id}/movie/{index}/skip/ endpoint."""

    @pytest.mark.asyncio
    async def test_skip_movie_success(self, client: AsyncClient, auth_headers: dict):
        """Test skipping a movie."""
        csv_file = create_test_csv([{"Type": "Movie", "Title": "Test"}])

        with patch("app.routers.import_amazon.matching.TMDBService") as mock_tmdb_class:
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

        response = await client.post(
            f"/api/v1/import/amazon-prime/session/{session_id}/movie/0/skip/",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify session updated
        session_response = await client.get(
            f"/api/v1/import/amazon-prime/session/{session_id}/",
            headers=auth_headers,
        )
        assert session_response.json()["skipped_count"] == 1

    @pytest.mark.asyncio
    async def test_skip_invalid_index_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test skipping with invalid index returns 404."""
        csv_file = create_test_csv([{"Type": "Movie", "Title": "Test"}])

        with patch("app.routers.import_amazon.matching.TMDBService") as mock_tmdb_class:
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

        response = await client.post(
            f"/api/v1/import/amazon-prime/session/{session_id}/movie/999/skip/",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_skip_already_processed_movie_returns_400(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test skipping already-processed movie returns 400."""
        csv_file = create_test_csv([{"Type": "Movie", "Title": "Test"}])

        with patch("app.routers.import_amazon.matching.TMDBService") as mock_tmdb_class:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.search_movies.return_value = [
                create_mock_tmdb_result(tmdb_id=77777, title="Test", year=2024)
            ]
            mock_tmdb_class.return_value = mock_instance

            upload_response = await client.post(
                "/api/v1/import/amazon-prime/upload/",
                files={"file": ("test.csv", csv_file, "text/csv")},
                headers=auth_headers,
            )

        session_id = upload_response.json()["session_id"]

        # Skip once
        await client.post(
            f"/api/v1/import/amazon-prime/session/{session_id}/movie/0/skip/",
            headers=auth_headers,
        )

        # Try to skip again
        response = await client.post(
            f"/api/v1/import/amazon-prime/session/{session_id}/movie/0/skip/",
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "already been processed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_skip_invalid_session_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test skipping with invalid session returns 404."""
        response = await client.post(
            "/api/v1/import/amazon-prime/session/invalid-session/movie/0/skip/",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_skip_without_auth_returns_401(self, client: AsyncClient):
        """Test skipping without auth returns 401."""
        response = await client.post(
            "/api/v1/import/amazon-prime/session/some-session/movie/0/skip/",
        )

        assert response.status_code == 401
