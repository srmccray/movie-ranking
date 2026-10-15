"""Tests for Amazon Prime import: full import flow.

NOTE: All URLs must include trailing slashes.
"""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from tests.import_amazon_helpers import create_mock_tmdb_result, create_test_csv


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
