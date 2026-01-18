"""Tests for Amazon Prime import endpoints.

These tests verify the import functionality including:
- CSV file upload and parsing
- TMDB matching
- Session management
- Movie add/skip workflow
- Error handling

NOTE: All URLs must include trailing slashes.
"""

import io
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient

from app.services.import_session import import_session_store


def create_test_csv(rows: list[dict]) -> io.BytesIO:
    """Create a CSV file in memory for testing.

    Args:
        rows: List of dicts with keys: Date Watched, Type, Title, Image URL

    Returns:
        BytesIO object containing CSV data.
    """
    content = "Date Watched,Type,Title,Episode Title,Global Title Identifier,Episode Global Title Identifier,Path,Episode Path,Image URL\n"
    for row in rows:
        content += f"{row.get('Date Watched', '')},{row.get('Type', 'Movie')},{row.get('Title', '')},,,,,,{row.get('Image URL', '')}\n"
    return io.BytesIO(content.encode("utf-8"))


def create_mock_tmdb_result(
    tmdb_id: int,
    title: str,
    year: int | None = None,
    poster_url: str | None = None,
    overview: str | None = None,
    genre_ids: list[int] | None = None,
    vote_average: float | None = None,
    vote_count: int | None = None,
    release_date: str | None = None,
    original_language: str | None = None,
):
    """Create a mock TMDB search result.

    All attributes must be explicitly set to avoid MagicMock returning
    nested MagicMock objects for unset attributes, which would cause
    Pydantic validation errors when creating TMDBMatchResult schemas.
    """
    mock = MagicMock()
    mock.tmdb_id = tmdb_id
    mock.title = title
    mock.year = year
    mock.poster_url = poster_url
    mock.overview = overview
    mock.genre_ids = genre_ids
    mock.vote_average = vote_average
    mock.vote_count = vote_count
    mock.release_date = release_date
    mock.original_language = original_language
    return mock


class TestUploadCSV:
    """Tests for POST /api/v1/import/amazon-prime/upload/ endpoint."""

    @pytest.mark.asyncio
    async def test_upload_valid_csv_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test successful CSV upload with movies."""
        csv_file = create_test_csv(
            [
                {"Type": "Movie", "Title": "The Matrix", "Date Watched": "2024-01-15"},
                {"Type": "Movie", "Title": "Inception", "Date Watched": "2024-02-20"},
                {"Type": "Series", "Title": "Breaking Bad"},  # Should be filtered
            ]
        )

        with patch("app.routers.import_amazon.TMDBService") as mock_tmdb_class:
            # Mock TMDB responses
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.search_movies.return_value = [
                create_mock_tmdb_result(
                    tmdb_id=603,
                    title="The Matrix",
                    year=1999,
                    poster_url="https://image.tmdb.org/t/p/w185/poster.jpg",
                    overview="A computer hacker learns...",
                )
            ]
            mock_tmdb_class.return_value = mock_instance

            response = await client.post(
                "/api/v1/import/amazon-prime/upload/",
                files={"file": ("watch_history.csv", csv_file, "text/csv")},
                headers=auth_headers,
            )

        assert response.status_code == 201
        data = response.json()
        assert "session_id" in data
        assert data["total_entries"] == 3
        assert data["movies_found"] == 2
        assert data["tv_shows_filtered"] == 1
        assert len(data["movies"]) >= 1  # At least one matched

    @pytest.mark.asyncio
    async def test_upload_without_auth_returns_401(self, client: AsyncClient):
        """Test that uploading without auth returns 401."""
        csv_file = create_test_csv(
            [
                {"Type": "Movie", "Title": "Test Movie"},
            ]
        )

        response = await client.post(
            "/api/v1/import/amazon-prime/upload/",
            files={"file": ("test.csv", csv_file, "text/csv")},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_upload_non_csv_returns_400(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that uploading non-CSV file returns 400."""
        response = await client.post(
            "/api/v1/import/amazon-prime/upload/",
            files={"file": ("test.txt", b"not a csv", "text/plain")},
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "CSV" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_empty_csv_returns_400(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that uploading empty CSV returns 400."""
        empty_csv = io.BytesIO(
            b"Date Watched,Type,Title,Episode Title,Global Title Identifier,Episode Global Title Identifier,Path,Episode Path,Image URL\n"
        )

        response = await client.post(
            "/api/v1/import/amazon-prime/upload/",
            files={"file": ("empty.csv", empty_csv, "text/csv")},
            headers=auth_headers,
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_only_tv_shows_returns_400(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that CSV with only TV shows returns 400."""
        csv_file = create_test_csv(
            [
                {"Type": "Series", "Title": "Breaking Bad"},
                {"Type": "Series", "Title": "The Office"},
            ]
        )

        response = await client.post(
            "/api/v1/import/amazon-prime/upload/",
            files={"file": ("tv_shows.csv", csv_file, "text/csv")},
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "No movies found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_response_structure(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that upload response has correct structure."""
        csv_file = create_test_csv(
            [
                {"Type": "Movie", "Title": "Test Movie", "Date Watched": "2024-01-15"},
            ]
        )

        with patch("app.routers.import_amazon.TMDBService") as mock_tmdb_class:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.search_movies.return_value = [
                create_mock_tmdb_result(
                    tmdb_id=1,
                    title="Test Movie",
                    year=2024,
                    poster_url=None,
                    overview="Test overview",
                )
            ]
            mock_tmdb_class.return_value = mock_instance

            response = await client.post(
                "/api/v1/import/amazon-prime/upload/",
                files={"file": ("test.csv", csv_file, "text/csv")},
                headers=auth_headers,
            )

        assert response.status_code == 201
        data = response.json()

        # Verify response structure
        assert "session_id" in data
        assert "total_entries" in data
        assert "movies_found" in data
        assert "tv_shows_filtered" in data
        assert "already_ranked" in data
        assert "ready_for_review" in data
        assert "movies" in data
        assert isinstance(data["movies"], list)


class TestGetSession:
    """Tests for GET /api/v1/import/amazon-prime/session/{session_id}/ endpoint."""

    @pytest.mark.asyncio
    async def test_get_valid_session(self, client: AsyncClient, auth_headers: dict):
        """Test getting a valid session."""
        # First create a session via upload
        csv_file = create_test_csv(
            [
                {"Type": "Movie", "Title": "Test Movie"},
            ]
        )

        with patch("app.routers.import_amazon.TMDBService") as mock_tmdb_class:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.search_movies.return_value = [
                create_mock_tmdb_result(
                    tmdb_id=1, title="Test Movie", year=2024, poster_url=None, overview=None
                )
            ]
            mock_tmdb_class.return_value = mock_instance

            upload_response = await client.post(
                "/api/v1/import/amazon-prime/upload/",
                files={"file": ("test.csv", csv_file, "text/csv")},
                headers=auth_headers,
            )

        session_id = upload_response.json()["session_id"]

        # Get the session
        response = await client.get(
            f"/api/v1/import/amazon-prime/session/{session_id}/",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["current_index"] == 0
        assert data["added_count"] == 0
        assert data["skipped_count"] == 0

    @pytest.mark.asyncio
    async def test_get_invalid_session_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting a non-existent session returns 404."""
        response = await client.get(
            "/api/v1/import/amazon-prime/session/invalid-session-id/",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_other_user_session_returns_404(self, client: AsyncClient):
        """Test that accessing another user's session returns 404."""
        # Create session with user 1
        user1_response = await client.post(
            "/api/v1/auth/register",
            json={"email": "user1@importtest.com", "password": "password123"},
        )
        user1_token = user1_response.json()["access_token"]
        user1_headers = {"Authorization": f"Bearer {user1_token}"}

        csv_file = create_test_csv([{"Type": "Movie", "Title": "Test"}])

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
                headers=user1_headers,
            )

        session_id = upload_response.json()["session_id"]

        # Try to access with user 2
        user2_response = await client.post(
            "/api/v1/auth/register",
            json={"email": "user2@importtest.com", "password": "password123"},
        )
        user2_token = user2_response.json()["access_token"]
        user2_headers = {"Authorization": f"Bearer {user2_token}"}

        response = await client.get(
            f"/api/v1/import/amazon-prime/session/{session_id}/",
            headers=user2_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_session_without_auth_returns_401(self, client: AsyncClient):
        """Test getting a session without auth returns 401."""
        response = await client.get(
            "/api/v1/import/amazon-prime/session/some-session-id/",
        )

        assert response.status_code == 401


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

        with patch("app.routers.import_amazon.TMDBService") as mock_tmdb_class:
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

        with patch("app.routers.import_amazon.TMDBService") as mock_tmdb_class:
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

        with patch("app.routers.import_amazon.TMDBService") as mock_tmdb_class:
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

        with patch("app.routers.import_amazon.TMDBService") as mock_tmdb_class:
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

        with patch("app.routers.import_amazon.TMDBService") as mock_tmdb_class:
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

        with patch("app.routers.import_amazon.TMDBService") as mock_tmdb_class:
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

        with patch("app.routers.import_amazon.TMDBService") as mock_tmdb_class:
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


class TestCancelSession:
    """Tests for DELETE /api/v1/import/amazon-prime/session/{session_id}/ endpoint."""

    @pytest.mark.asyncio
    async def test_cancel_session_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test cancelling a session."""
        csv_file = create_test_csv([{"Type": "Movie", "Title": "Test"}])

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

        # Cancel
        response = await client.delete(
            f"/api/v1/import/amazon-prime/session/{session_id}/",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify session is gone
        get_response = await client.get(
            f"/api/v1/import/amazon-prime/session/{session_id}/",
            headers=auth_headers,
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_invalid_session_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test cancelling a non-existent session returns 404."""
        response = await client.delete(
            "/api/v1/import/amazon-prime/session/invalid-session-id/",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_other_user_session_returns_404(self, client: AsyncClient):
        """Test cancelling another user's session returns 404."""
        # Create session with user 1
        user1_response = await client.post(
            "/api/v1/auth/register",
            json={"email": "cancel_user1@importtest.com", "password": "password123"},
        )
        user1_token = user1_response.json()["access_token"]
        user1_headers = {"Authorization": f"Bearer {user1_token}"}

        csv_file = create_test_csv([{"Type": "Movie", "Title": "Test"}])

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
                headers=user1_headers,
            )

        session_id = upload_response.json()["session_id"]

        # Try to cancel as user 2
        user2_response = await client.post(
            "/api/v1/auth/register",
            json={"email": "cancel_user2@importtest.com", "password": "password123"},
        )
        user2_token = user2_response.json()["access_token"]
        user2_headers = {"Authorization": f"Bearer {user2_token}"}

        response = await client.delete(
            f"/api/v1/import/amazon-prime/session/{session_id}/",
            headers=user2_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_without_auth_returns_401(self, client: AsyncClient):
        """Test cancelling without auth returns 401."""
        response = await client.delete(
            "/api/v1/import/amazon-prime/session/some-session/",
        )

        assert response.status_code == 401


class TestFullImportFlow:
    """Integration tests for complete import flows."""

    @pytest.mark.asyncio
    async def test_complete_import_flow(self, client: AsyncClient):
        """Test complete upload -> review -> add/skip flow."""
        # Register user
        register_response = await client.post(
            "/api/v1/auth/register",
            json={"email": "flow@importtest.com", "password": "password123"},
        )
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Upload CSV with multiple movies
        csv_file = create_test_csv(
            [
                {"Type": "Movie", "Title": "Movie 1", "Date Watched": "2024-01-01"},
                {"Type": "Movie", "Title": "Movie 2", "Date Watched": "2024-02-01"},
                {"Type": "Movie", "Title": "Movie 3", "Date Watched": "2024-03-01"},
            ]
        )

        with patch("app.routers.import_amazon.TMDBService") as mock_tmdb_class:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None

            # Return different results for each search
            mock_instance.search_movies.side_effect = [
                [create_mock_tmdb_result(tmdb_id=100, title="Movie 1", year=2024)],
                [create_mock_tmdb_result(tmdb_id=200, title="Movie 2", year=2024)],
                [create_mock_tmdb_result(tmdb_id=300, title="Movie 3", year=2024)],
            ]
            mock_tmdb_class.return_value = mock_instance

            upload_response = await client.post(
                "/api/v1/import/amazon-prime/upload/",
                files={"file": ("movies.csv", csv_file, "text/csv")},
                headers=headers,
            )

        assert upload_response.status_code == 201
        session_id = upload_response.json()["session_id"]

        # Add first movie
        add_response = await client.post(
            f"/api/v1/import/amazon-prime/session/{session_id}/movie/0/add/",
            json={"rating": 5},
            headers=headers,
        )
        assert add_response.status_code == 201

        # Skip second movie
        skip_response = await client.post(
            f"/api/v1/import/amazon-prime/session/{session_id}/movie/1/skip/",
            headers=headers,
        )
        assert skip_response.status_code == 204

        # Add third movie
        add_response2 = await client.post(
            f"/api/v1/import/amazon-prime/session/{session_id}/movie/2/add/",
            json={"rating": 3},
            headers=headers,
        )
        assert add_response2.status_code == 201

        # Check final session state
        session_response = await client.get(
            f"/api/v1/import/amazon-prime/session/{session_id}/",
            headers=headers,
        )
        data = session_response.json()
        assert data["added_count"] == 2
        assert data["skipped_count"] == 1
        assert data["remaining_count"] == 0

        # Verify rankings were created
        rankings_response = await client.get(
            "/api/v1/rankings/",
            headers=headers,
        )
        assert rankings_response.json()["total"] == 2

    @pytest.mark.asyncio
    async def test_import_flow_with_cancel(self, client: AsyncClient):
        """Test import flow with session cancellation."""
        # Register user
        register_response = await client.post(
            "/api/v1/auth/register",
            json={"email": "cancel_flow@importtest.com", "password": "password123"},
        )
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Upload CSV
        csv_file = create_test_csv(
            [
                {"Type": "Movie", "Title": "Movie 1"},
                {"Type": "Movie", "Title": "Movie 2"},
            ]
        )

        with patch("app.routers.import_amazon.TMDBService") as mock_tmdb_class:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.search_movies.side_effect = [
                [create_mock_tmdb_result(tmdb_id=500, title="Movie 1", year=2024)],
                [create_mock_tmdb_result(tmdb_id=600, title="Movie 2", year=2024)],
            ]
            mock_tmdb_class.return_value = mock_instance

            upload_response = await client.post(
                "/api/v1/import/amazon-prime/upload/",
                files={"file": ("movies.csv", csv_file, "text/csv")},
                headers=headers,
            )

        session_id = upload_response.json()["session_id"]

        # Add first movie
        await client.post(
            f"/api/v1/import/amazon-prime/session/{session_id}/movie/0/add/",
            json={"rating": 4},
            headers=headers,
        )

        # Cancel session (abandoning second movie)
        cancel_response = await client.delete(
            f"/api/v1/import/amazon-prime/session/{session_id}/",
            headers=headers,
        )
        assert cancel_response.status_code == 204

        # Verify session is gone
        get_response = await client.get(
            f"/api/v1/import/amazon-prime/session/{session_id}/",
            headers=headers,
        )
        assert get_response.status_code == 404

        # Ranking from before cancel should still exist
        rankings_response = await client.get(
            "/api/v1/rankings/",
            headers=headers,
        )
        assert rankings_response.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_new_upload_replaces_existing_session(self, client: AsyncClient):
        """Test that new upload replaces existing import session."""
        # Register user
        register_response = await client.post(
            "/api/v1/auth/register",
            json={"email": "replace@importtest.com", "password": "password123"},
        )
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # First upload
        csv_file_1 = create_test_csv([{"Type": "Movie", "Title": "First Movie"}])

        with patch("app.routers.import_amazon.TMDBService") as mock_tmdb_class:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.search_movies.return_value = [
                create_mock_tmdb_result(tmdb_id=1001, title="First Movie", year=2024)
            ]
            mock_tmdb_class.return_value = mock_instance

            upload_response_1 = await client.post(
                "/api/v1/import/amazon-prime/upload/",
                files={"file": ("first.csv", csv_file_1, "text/csv")},
                headers=headers,
            )

        session_id_1 = upload_response_1.json()["session_id"]

        # Second upload (should replace first)
        csv_file_2 = create_test_csv([{"Type": "Movie", "Title": "Second Movie"}])

        with patch("app.routers.import_amazon.TMDBService") as mock_tmdb_class:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.search_movies.return_value = [
                create_mock_tmdb_result(tmdb_id=1002, title="Second Movie", year=2024)
            ]
            mock_tmdb_class.return_value = mock_instance

            upload_response_2 = await client.post(
                "/api/v1/import/amazon-prime/upload/",
                files={"file": ("second.csv", csv_file_2, "text/csv")},
                headers=headers,
            )

        session_id_2 = upload_response_2.json()["session_id"]

        # Session IDs should be different
        assert session_id_1 != session_id_2

        # Old session should be gone
        get_response_1 = await client.get(
            f"/api/v1/import/amazon-prime/session/{session_id_1}/",
            headers=headers,
        )
        assert get_response_1.status_code == 404

        # New session should exist
        get_response_2 = await client.get(
            f"/api/v1/import/amazon-prime/session/{session_id_2}/",
            headers=headers,
        )
        assert get_response_2.status_code == 200
