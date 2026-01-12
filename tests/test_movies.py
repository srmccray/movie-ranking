"""Tests for movies endpoints.

These tests verify the movies functionality including:
- Creating movies with all fields (title, year, tmdb_id, poster_url)
- Searching movies via TMDB API
- Authentication requirements
- Input validation
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


class TestCreateMovie:
    """Tests for POST /api/v1/movies/ endpoint."""

    @pytest.mark.asyncio
    async def test_create_movie_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test successful movie creation with basic fields."""
        response = await client.post(
            "/api/v1/movies/",
            json={
                "title": "The Matrix",
                "year": 1999,
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "The Matrix"
        assert data["year"] == 1999
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_movie_with_tmdb_id(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating movie with TMDB ID."""
        response = await client.post(
            "/api/v1/movies/",
            json={
                "title": "The Matrix",
                "year": 1999,
                "tmdb_id": 603,
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["tmdb_id"] == 603

    @pytest.mark.asyncio
    async def test_create_movie_with_poster_url(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating movie with poster URL."""
        poster_url = "https://image.tmdb.org/t/p/w185/abc123.jpg"
        response = await client.post(
            "/api/v1/movies/",
            json={
                "title": "The Matrix",
                "year": 1999,
                "poster_url": poster_url,
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["poster_url"] == poster_url

    @pytest.mark.asyncio
    async def test_create_movie_with_all_fields(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating movie with all optional fields."""
        response = await client.post(
            "/api/v1/movies/",
            json={
                "title": "The Matrix",
                "year": 1999,
                "tmdb_id": 603,
                "poster_url": "https://image.tmdb.org/t/p/w185/abc123.jpg",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "The Matrix"
        assert data["year"] == 1999
        assert data["tmdb_id"] == 603
        assert data["poster_url"] == "https://image.tmdb.org/t/p/w185/abc123.jpg"

    @pytest.mark.asyncio
    async def test_create_movie_without_optional_fields(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating movie without optional fields."""
        response = await client.post(
            "/api/v1/movies/",
            json={
                "title": "Mystery Movie",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Mystery Movie"
        assert data["year"] is None
        assert data["tmdb_id"] is None
        assert data["poster_url"] is None

    @pytest.mark.asyncio
    async def test_create_movie_without_auth_returns_401(
        self, client: AsyncClient
    ):
        """Test that creating movie without auth returns 401."""
        response = await client.post(
            "/api/v1/movies/",
            json={"title": "Test Movie"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_movie_missing_title_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that missing title returns 422 validation error."""
        response = await client.post(
            "/api/v1/movies/",
            json={
                "year": 2024,
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_movie_empty_title_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that empty title returns 422 validation error."""
        response = await client.post(
            "/api/v1/movies/",
            json={
                "title": "",
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_movie_invalid_year_too_old_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that year before 1888 returns 422 validation error."""
        response = await client.post(
            "/api/v1/movies/",
            json={
                "title": "Ancient Movie",
                "year": 1800,
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_movie_invalid_year_future_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that year too far in future returns 422 validation error."""
        response = await client.post(
            "/api/v1/movies/",
            json={
                "title": "Future Movie",
                "year": 2050,
            },
            headers=auth_headers,
        )

        assert response.status_code == 422


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


class TestMovieSearchAndCreate:
    """Integration tests for searching and then creating a movie."""

    @pytest.mark.asyncio
    async def test_search_then_create_movie(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test workflow of searching TMDB then creating a movie from results."""
        mock_results = [
            TMDBMovieResult(
                tmdb_id=603,
                title="The Matrix",
                year=1999,
                poster_path="/abc123.jpg",
                poster_url="https://image.tmdb.org/t/p/w185/abc123.jpg",
                overview="A computer hacker.",
            ),
        ]

        with patch(
            "app.routers.movies.TMDBService"
        ) as MockTMDBService:
            mock_service = AsyncMock()
            mock_service.__aenter__.return_value = mock_service
            mock_service.__aexit__.return_value = None
            mock_service.search_movies.return_value = mock_results
            MockTMDBService.return_value = mock_service

            # Step 1: Search for movie
            search_response = await client.get(
                "/api/v1/movies/search/",
                params={"q": "matrix"},
                headers=auth_headers,
            )

        assert search_response.status_code == 200
        search_data = search_response.json()
        assert len(search_data["results"]) == 1

        # Step 2: Create movie using search result data
        tmdb_result = search_data["results"][0]
        create_response = await client.post(
            "/api/v1/movies/",
            json={
                "title": tmdb_result["title"],
                "year": tmdb_result["year"],
                "tmdb_id": tmdb_result["tmdb_id"],
                "poster_url": tmdb_result["poster_url"],
            },
            headers=auth_headers,
        )

        assert create_response.status_code == 201
        movie_data = create_response.json()
        assert movie_data["title"] == "The Matrix"
        assert movie_data["year"] == 1999
        assert movie_data["tmdb_id"] == 603
        assert movie_data["poster_url"] == "https://image.tmdb.org/t/p/w185/abc123.jpg"

    @pytest.mark.asyncio
    async def test_full_flow_search_create_rank(
        self, client: AsyncClient
    ):
        """Test complete workflow: register, search, create movie, rank it."""
        # Step 1: Register user
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "moviefan@example.com",
                "password": "password123",
            },
        )
        assert register_response.status_code == 201
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Step 2: Search for movie
        mock_results = [
            TMDBMovieResult(
                tmdb_id=603,
                title="The Matrix",
                year=1999,
                poster_path="/abc123.jpg",
                poster_url="https://image.tmdb.org/t/p/w185/abc123.jpg",
                overview="A computer hacker.",
            ),
        ]

        with patch(
            "app.routers.movies.TMDBService"
        ) as MockTMDBService:
            mock_service = AsyncMock()
            mock_service.__aenter__.return_value = mock_service
            mock_service.__aexit__.return_value = None
            mock_service.search_movies.return_value = mock_results
            MockTMDBService.return_value = mock_service

            search_response = await client.get(
                "/api/v1/movies/search/",
                params={"q": "matrix"},
                headers=headers,
            )

        assert search_response.status_code == 200
        tmdb_result = search_response.json()["results"][0]

        # Step 3: Create movie from search result
        create_response = await client.post(
            "/api/v1/movies/",
            json={
                "title": tmdb_result["title"],
                "year": tmdb_result["year"],
                "tmdb_id": tmdb_result["tmdb_id"],
                "poster_url": tmdb_result["poster_url"],
            },
            headers=headers,
        )
        assert create_response.status_code == 201
        movie_id = create_response.json()["id"]

        # Step 4: Rank the movie
        ranking_response = await client.post(
            "/api/v1/rankings/",
            json={
                "movie_id": movie_id,
                "rating": 5,
            },
            headers=headers,
        )
        assert ranking_response.status_code == 201
        assert ranking_response.json()["rating"] == 5

        # Step 5: Verify ranking in list
        list_response = await client.get(
            "/api/v1/rankings/",
            headers=headers,
        )
        assert list_response.status_code == 200
        rankings = list_response.json()["items"]
        assert len(rankings) == 1
        assert rankings[0]["movie"]["title"] == "The Matrix"
        assert rankings[0]["movie"]["poster_url"] == "https://image.tmdb.org/t/p/w185/abc123.jpg"
