"""Tests for Amazon Prime import: CSV upload, session retrieval and cancel.

NOTE: All URLs must include trailing slashes.
"""

import io
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from tests.import_amazon_helpers import create_mock_tmdb_result, create_test_csv


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

        with patch("app.routers.import_amazon.matching.TMDBService") as mock_tmdb_class:
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

        with patch("app.routers.import_amazon.matching.TMDBService") as mock_tmdb_class:
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

        with patch("app.routers.import_amazon.matching.TMDBService") as mock_tmdb_class:
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


class TestCancelSession:
    """Tests for DELETE /api/v1/import/amazon-prime/session/{session_id}/ endpoint."""

    @pytest.mark.asyncio
    async def test_cancel_session_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test cancelling a session."""
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
