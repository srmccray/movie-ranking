"""Tests for the movie search endpoint.

These tests verify searching movies via the TMDB API, authentication
requirements and input validation.
"""

import pytest
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from app.services.tmdb import (
    TMDBMovieResult,
    TMDBRateLimitError,
    TMDBAPIError,
    TMDBServiceError,
)


class TestSearchMovies:
    """Tests for GET /api/v1/movies/search/ endpoint."""

    @pytest.fixture
    def mock_tmdb_results(self):
        """Sample TMDB search results."""
        return [
            TMDBMovieResult(
                tmdb_id=603,
                title="The Matrix",
                year=1999,
                poster_path="/abc123.jpg",
                poster_url="https://image.tmdb.org/t/p/w185/abc123.jpg",
                overview="A computer hacker learns about reality.",
            ),
            TMDBMovieResult(
                tmdb_id=604,
                title="The Matrix Reloaded",
                year=2003,
                poster_path="/def456.jpg",
                poster_url="https://image.tmdb.org/t/p/w185/def456.jpg",
                overview="Neo continues his mission.",
            ),
        ]

    @pytest.mark.asyncio
    async def test_search_movies_returns_results(
        self, client: AsyncClient, auth_headers: dict, mock_tmdb_results
    ):
        """Test search endpoint returns TMDB results."""
        with patch(
            "app.routers.movies.TMDBService"
        ) as MockTMDBService:
            mock_service = AsyncMock()
            mock_service.__aenter__.return_value = mock_service
            mock_service.__aexit__.return_value = None
            mock_service.search_movies.return_value = mock_tmdb_results
            MockTMDBService.return_value = mock_service

            response = await client.get(
                "/api/v1/movies/search/",
                params={"q": "matrix"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 2
        assert data["results"][0]["title"] == "The Matrix"
        assert data["results"][0]["tmdb_id"] == 603
        assert data["results"][0]["year"] == 1999
        assert data["results"][0]["poster_url"] == "https://image.tmdb.org/t/p/w185/abc123.jpg"
        assert data["query"] == "matrix"

    @pytest.mark.asyncio
    async def test_search_movies_with_year_filter(
        self, client: AsyncClient, auth_headers: dict, mock_tmdb_results
    ):
        """Test search endpoint passes year filter to TMDB."""
        with patch(
            "app.routers.movies.TMDBService"
        ) as MockTMDBService:
            mock_service = AsyncMock()
            mock_service.__aenter__.return_value = mock_service
            mock_service.__aexit__.return_value = None
            mock_service.search_movies.return_value = [mock_tmdb_results[0]]
            MockTMDBService.return_value = mock_service

            response = await client.get(
                "/api/v1/movies/search/",
                params={"q": "matrix", "year": 1999},
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["year"] == 1999
        # Verify the year was passed to TMDB service
        mock_service.search_movies.assert_called_once_with(query="matrix", year=1999)

    @pytest.mark.asyncio
    async def test_search_movies_empty_results(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test search endpoint returns empty results for no matches."""
        with patch(
            "app.routers.movies.TMDBService"
        ) as MockTMDBService:
            mock_service = AsyncMock()
            mock_service.__aenter__.return_value = mock_service
            mock_service.__aexit__.return_value = None
            mock_service.search_movies.return_value = []
            MockTMDBService.return_value = mock_service

            response = await client.get(
                "/api/v1/movies/search/",
                params={"q": "nonexistentmovie12345"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []
        assert data["query"] == "nonexistentmovie12345"

    @pytest.mark.asyncio
    async def test_search_movies_requires_authentication(
        self, client: AsyncClient
    ):
        """Test search endpoint requires authentication."""
        response = await client.get(
            "/api/v1/movies/search/",
            params={"q": "matrix"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_search_movies_missing_query_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test search without query parameter returns 422."""
        response = await client.get(
            "/api/v1/movies/search/",
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_movies_empty_query_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test search with empty query returns 422."""
        response = await client.get(
            "/api/v1/movies/search/",
            params={"q": ""},
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_movies_rate_limit_returns_503(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test search returns 503 when TMDB rate limit exceeded."""
        with patch(
            "app.routers.movies.TMDBService"
        ) as MockTMDBService:
            mock_service = AsyncMock()
            mock_service.__aenter__.return_value = mock_service
            mock_service.__aexit__.return_value = None
            mock_service.search_movies.side_effect = TMDBRateLimitError(
                "Rate limit exceeded"
            )
            MockTMDBService.return_value = mock_service

            response = await client.get(
                "/api/v1/movies/search/",
                params={"q": "matrix"},
                headers=auth_headers,
            )

        assert response.status_code == 503
        data = response.json()
        assert "rate limit" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_search_movies_api_error_returns_500(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test search returns 500 when TMDB API error occurs."""
        with patch(
            "app.routers.movies.TMDBService"
        ) as MockTMDBService:
            mock_service = AsyncMock()
            mock_service.__aenter__.return_value = mock_service
            mock_service.__aexit__.return_value = None
            mock_service.search_movies.side_effect = TMDBAPIError(
                "Invalid API key"
            )
            MockTMDBService.return_value = mock_service

            response = await client.get(
                "/api/v1/movies/search/",
                params={"q": "matrix"},
                headers=auth_headers,
            )

        assert response.status_code == 500
        data = response.json()
        assert "failed" in data["detail"].lower() or "error" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_search_movies_service_error_returns_500(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test search returns 500 when TMDB service error occurs."""
        with patch(
            "app.routers.movies.TMDBService"
        ) as MockTMDBService:
            mock_service = AsyncMock()
            mock_service.__aenter__.return_value = mock_service
            mock_service.__aexit__.return_value = None
            mock_service.search_movies.side_effect = TMDBServiceError(
                "Connection failed"
            )
            MockTMDBService.return_value = mock_service

            response = await client.get(
                "/api/v1/movies/search/",
                params={"q": "matrix"},
                headers=auth_headers,
            )

        assert response.status_code == 500
        data = response.json()
        assert "unavailable" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_search_movies_year_validation_min(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test search with year before 1888 returns 422."""
        response = await client.get(
            "/api/v1/movies/search/",
            params={"q": "test", "year": 1800},
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_movies_year_validation_max(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test search with year after 2031 returns 422."""
        response = await client.get(
            "/api/v1/movies/search/",
            params={"q": "test", "year": 2050},
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_movies_query_max_length(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test search with query exceeding max length returns 422."""
        long_query = "x" * 250  # Exceeds 200 character limit

        response = await client.get(
            "/api/v1/movies/search/",
            params={"q": long_query},
            headers=auth_headers,
        )

        assert response.status_code == 422
