# Task 06: Backend Integration Tests

**Feature:** amazon-prime-import
**Agent:** test-coverage
**Status:** Not Started
**Blocked By:** 03

---

## Objective

Create comprehensive integration tests for the Amazon Prime import API endpoints, covering the full upload-to-ranking workflow, error handling, and edge cases.

---

## Context

The backend implementation is complete. This task adds test coverage to ensure the import feature works correctly and handles edge cases gracefully.

### Relevant FRD Sections
- FRD Section: "Testing Strategy" - Required test scenarios
- FRD Section: "Acceptance Criteria" - Feature requirements to verify

### Relevant Refinement Notes
- Test full upload-to-ranking flow
- Test session expiry handling
- Test already-ranked movie filtering

---

## Scope

### In Scope
- Create `tests/test_import_amazon.py` with integration tests
- Test CSV upload endpoint with various file scenarios
- Test session retrieval and state management
- Test add/skip movie actions
- Test session cancellation
- Test authorization (user ownership)
- Test error handling (expired sessions, invalid data)

### Out of Scope
- Frontend tests (handled separately)
- Unit tests for individual services (optional, bonus)

---

## Implementation Notes

### Key Files

| File | Action | Notes |
|------|--------|-------|
| `/Users/stephen/Projects/movie-ranking/tests/test_import_amazon.py` | Create | Integration tests |

### Patterns to Follow

- Test pattern: See `/Users/stephen/Projects/movie-ranking/tests/test_rankings.py`
- Fixtures: Use `client`, `auth_headers`, `test_user` from conftest.py
- Mocking: Mock TMDB service for deterministic results

### Test File Structure

```python
# tests/test_import_amazon.py

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
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


def create_test_csv(rows: list[dict]) -> io.BytesIO:
    """Create a CSV file in memory for testing.

    Args:
        rows: List of dicts with keys: Date Watched, Type, Title, Image URL

    Returns:
        BytesIO object containing CSV data.
    """
    content = "Date Watched,Type,Title,Episode Title,Global Title Identifier,Episode Global Title Identifier,Path,Episode Path,Image URL\n"
    for row in rows:
        content += f"{row.get('Date Watched', '')},{row.get('Type', 'Movie')},{row.get('Title', '')},,,,,{row.get('Image URL', '')}\n"
    return io.BytesIO(content.encode('utf-8'))


class TestUploadCSV:
    """Tests for POST /api/v1/import/amazon-prime/upload/ endpoint."""

    @pytest.mark.asyncio
    async def test_upload_valid_csv_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test successful CSV upload with movies."""
        csv_file = create_test_csv([
            {"Type": "Movie", "Title": "The Matrix", "Date Watched": "2024-01-15"},
            {"Type": "Movie", "Title": "Inception", "Date Watched": "2024-02-20"},
            {"Type": "Series", "Title": "Breaking Bad"},  # Should be filtered
        ])

        with patch('app.routers.import_amazon.TMDBService') as mock_tmdb:
            # Mock TMDB responses
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.search_movies.return_value = [
                AsyncMock(
                    tmdb_id=603,
                    title="The Matrix",
                    year=1999,
                    poster_url="https://image.tmdb.org/t/p/w185/poster.jpg",
                    overview="A computer hacker learns..."
                )
            ]
            mock_tmdb.return_value = mock_instance

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
    async def test_upload_without_auth_returns_401(
        self, client: AsyncClient
    ):
        """Test that uploading without auth returns 401."""
        csv_file = create_test_csv([
            {"Type": "Movie", "Title": "Test Movie"},
        ])

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
        empty_csv = io.BytesIO(b"Date Watched,Type,Title\n")

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
        csv_file = create_test_csv([
            {"Type": "Series", "Title": "Breaking Bad"},
            {"Type": "Series", "Title": "The Office"},
        ])

        response = await client.post(
            "/api/v1/import/amazon-prime/upload/",
            files={"file": ("tv_shows.csv", csv_file, "text/csv")},
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "No movies found" in response.json()["detail"]


class TestGetSession:
    """Tests for GET /api/v1/import/amazon-prime/session/{session_id}/ endpoint."""

    @pytest.mark.asyncio
    async def test_get_valid_session(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting a valid session."""
        # First create a session via upload
        csv_file = create_test_csv([
            {"Type": "Movie", "Title": "Test Movie"},
        ])

        with patch('app.routers.import_amazon.TMDBService') as mock_tmdb:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.search_movies.return_value = [
                AsyncMock(
                    tmdb_id=1,
                    title="Test Movie",
                    year=2024,
                    poster_url=None,
                    overview=None
                )
            ]
            mock_tmdb.return_value = mock_instance

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
    async def test_get_other_user_session_returns_404(
        self, client: AsyncClient
    ):
        """Test that accessing another user's session returns 404."""
        # Create session with user 1
        user1_response = await client.post(
            "/api/v1/auth/register",
            json={"email": "user1@import.test", "password": "password123"},
        )
        user1_token = user1_response.json()["access_token"]
        user1_headers = {"Authorization": f"Bearer {user1_token}"}

        csv_file = create_test_csv([{"Type": "Movie", "Title": "Test"}])

        with patch('app.routers.import_amazon.TMDBService') as mock_tmdb:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.search_movies.return_value = [
                AsyncMock(tmdb_id=1, title="Test", year=2024, poster_url=None, overview=None)
            ]
            mock_tmdb.return_value = mock_instance

            upload_response = await client.post(
                "/api/v1/import/amazon-prime/upload/",
                files={"file": ("test.csv", csv_file, "text/csv")},
                headers=user1_headers,
            )

        session_id = upload_response.json()["session_id"]

        # Try to access with user 2
        user2_response = await client.post(
            "/api/v1/auth/register",
            json={"email": "user2@import.test", "password": "password123"},
        )
        user2_token = user2_response.json()["access_token"]
        user2_headers = {"Authorization": f"Bearer {user2_token}"}

        response = await client.get(
            f"/api/v1/import/amazon-prime/session/{session_id}/",
            headers=user2_headers,
        )

        assert response.status_code == 404


class TestAddMovie:
    """Tests for POST /api/v1/import/amazon-prime/session/{session_id}/movie/{index}/add/ endpoint."""

    @pytest.mark.asyncio
    async def test_add_movie_creates_ranking(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test adding a movie creates a ranking."""
        # Create session
        csv_file = create_test_csv([
            {"Type": "Movie", "Title": "Test Movie", "Date Watched": "2024-01-15"},
        ])

        with patch('app.routers.import_amazon.TMDBService') as mock_tmdb:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.search_movies.return_value = [
                AsyncMock(tmdb_id=12345, title="Test Movie", year=2024, poster_url=None, overview=None)
            ]
            mock_tmdb.return_value = mock_instance

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

    @pytest.mark.asyncio
    async def test_add_movie_with_custom_rated_at(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test adding a movie with custom rated_at."""
        csv_file = create_test_csv([
            {"Type": "Movie", "Title": "Test Movie"},
        ])

        with patch('app.routers.import_amazon.TMDBService') as mock_tmdb:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.search_movies.return_value = [
                AsyncMock(tmdb_id=99999, title="Test Movie", year=2024, poster_url=None, overview=None)
            ]
            mock_tmdb.return_value = mock_instance

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
        # Note: rated_at is stored as naive UTC, so exact comparison needs care

    @pytest.mark.asyncio
    async def test_add_movie_invalid_rating_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test adding movie with invalid rating returns 422."""
        csv_file = create_test_csv([{"Type": "Movie", "Title": "Test"}])

        with patch('app.routers.import_amazon.TMDBService') as mock_tmdb:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.search_movies.return_value = [
                AsyncMock(tmdb_id=1, title="Test", year=2024, poster_url=None, overview=None)
            ]
            mock_tmdb.return_value = mock_instance

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
    async def test_add_already_processed_movie_returns_400(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test adding already-processed movie returns 400."""
        csv_file = create_test_csv([{"Type": "Movie", "Title": "Test"}])

        with patch('app.routers.import_amazon.TMDBService') as mock_tmdb:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.search_movies.return_value = [
                AsyncMock(tmdb_id=88888, title="Test", year=2024, poster_url=None, overview=None)
            ]
            mock_tmdb.return_value = mock_instance

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


class TestSkipMovie:
    """Tests for POST /api/v1/import/amazon-prime/session/{session_id}/movie/{index}/skip/ endpoint."""

    @pytest.mark.asyncio
    async def test_skip_movie_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test skipping a movie."""
        csv_file = create_test_csv([{"Type": "Movie", "Title": "Test"}])

        with patch('app.routers.import_amazon.TMDBService') as mock_tmdb:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.search_movies.return_value = [
                AsyncMock(tmdb_id=1, title="Test", year=2024, poster_url=None, overview=None)
            ]
            mock_tmdb.return_value = mock_instance

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

        with patch('app.routers.import_amazon.TMDBService') as mock_tmdb:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.search_movies.return_value = [
                AsyncMock(tmdb_id=1, title="Test", year=2024, poster_url=None, overview=None)
            ]
            mock_tmdb.return_value = mock_instance

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


class TestCancelSession:
    """Tests for DELETE /api/v1/import/amazon-prime/session/{session_id}/ endpoint."""

    @pytest.mark.asyncio
    async def test_cancel_session_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test cancelling a session."""
        csv_file = create_test_csv([{"Type": "Movie", "Title": "Test"}])

        with patch('app.routers.import_amazon.TMDBService') as mock_tmdb:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.search_movies.return_value = [
                AsyncMock(tmdb_id=1, title="Test", year=2024, poster_url=None, overview=None)
            ]
            mock_tmdb.return_value = mock_instance

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


class TestFullImportFlow:
    """Integration tests for complete import flows."""

    @pytest.mark.asyncio
    async def test_complete_import_flow(
        self, client: AsyncClient
    ):
        """Test complete upload -> review -> add/skip flow."""
        # Register user
        register_response = await client.post(
            "/api/v1/auth/register",
            json={"email": "flow@import.test", "password": "password123"},
        )
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Upload CSV with multiple movies
        csv_file = create_test_csv([
            {"Type": "Movie", "Title": "Movie 1", "Date Watched": "2024-01-01"},
            {"Type": "Movie", "Title": "Movie 2", "Date Watched": "2024-02-01"},
            {"Type": "Movie", "Title": "Movie 3", "Date Watched": "2024-03-01"},
        ])

        with patch('app.routers.import_amazon.TMDBService') as mock_tmdb:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None

            # Return different results for each search
            mock_instance.search_movies.side_effect = [
                [AsyncMock(tmdb_id=100, title="Movie 1", year=2024, poster_url=None, overview=None)],
                [AsyncMock(tmdb_id=200, title="Movie 2", year=2024, poster_url=None, overview=None)],
                [AsyncMock(tmdb_id=300, title="Movie 3", year=2024, poster_url=None, overview=None)],
            ]
            mock_tmdb.return_value = mock_instance

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
```

---

## Acceptance Criteria

- [ ] Upload tests cover valid CSV, empty CSV, non-CSV, TV-only CSV
- [ ] Upload tests verify response structure matches schema
- [ ] Session tests cover valid session, invalid session, wrong user
- [ ] Add movie tests cover success, invalid rating, already processed
- [ ] Add movie tests verify ranking is created
- [ ] Skip movie tests cover success, invalid index
- [ ] Cancel session tests verify session is deleted
- [ ] Full flow test covers upload -> add/skip -> complete
- [ ] All tests use trailing slashes in URLs
- [ ] All tests handle auth correctly
- [ ] TMDB service is mocked for deterministic results

---

## Testing Requirements

- [ ] All tests pass with `pytest tests/test_import_amazon.py -v`
- [ ] Tests are isolated (no state leakage between tests)
- [ ] Tests use appropriate fixtures
- [ ] Error messages are verified, not just status codes

---

## Handoff Notes

### Feature Complete
After this task, the Amazon Prime Import feature is:
- Fully implemented (backend + frontend)
- Fully tested (integration tests)
- Ready for manual testing and deployment

### Artifacts Produced
- `/Users/stephen/Projects/movie-ranking/tests/test_import_amazon.py`
