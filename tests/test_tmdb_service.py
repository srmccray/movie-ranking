"""Tests for TMDB service.

These tests verify the TMDB service functionality including:
- Search movies returns results
- Search with year filter
- Error handling (rate limits, API errors, timeouts)
- Response parsing

All tests use mocking to avoid making real API calls.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.services.tmdb import (
    TMDBService,
    TMDBMovieResult,
    TMDBRateLimitError,
    TMDBAPIError,
    TMDBServiceError,
    search_movies,
)


class TestTMDBMovieResult:
    """Tests for TMDBMovieResult dataclass."""

    def test_movie_result_with_all_fields(self):
        """Test creating a movie result with all fields populated."""
        result = TMDBMovieResult(
            tmdb_id=603,
            title="The Matrix",
            year=1999,
            poster_path="/abc123.jpg",
            poster_url="https://image.tmdb.org/t/p/w185/abc123.jpg",
            overview="A computer hacker learns about the true nature of reality.",
        )

        assert result.tmdb_id == 603
        assert result.title == "The Matrix"
        assert result.year == 1999
        assert result.poster_path == "/abc123.jpg"
        assert result.poster_url == "https://image.tmdb.org/t/p/w185/abc123.jpg"
        assert result.overview == "A computer hacker learns about the true nature of reality."

    def test_movie_result_with_optional_fields_none(self):
        """Test creating a movie result with optional fields as None."""
        result = TMDBMovieResult(
            tmdb_id=12345,
            title="Unknown Movie",
            year=None,
            poster_path=None,
            poster_url=None,
            overview=None,
        )

        assert result.tmdb_id == 12345
        assert result.title == "Unknown Movie"
        assert result.year is None
        assert result.poster_path is None
        assert result.poster_url is None
        assert result.overview is None


class TestTMDBServiceHelpers:
    """Tests for TMDBService helper methods."""

    @pytest.fixture
    def service(self):
        """Create a TMDBService instance with mocked settings."""
        with patch("app.services.tmdb.settings") as mock_settings:
            mock_settings.TMDB_API_KEY = "test-api-key"
            mock_settings.TMDB_BASE_URL = "https://api.themoviedb.org/3"
            mock_settings.TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w185"
            yield TMDBService()

    def test_build_poster_url_with_path(self, service):
        """Test building full poster URL from path."""
        result = service._build_poster_url("/abc123.jpg")
        assert result == "https://image.tmdb.org/t/p/w185/abc123.jpg"

    def test_build_poster_url_with_none(self, service):
        """Test building poster URL returns None when path is None."""
        result = service._build_poster_url(None)
        assert result is None

    def test_build_poster_url_with_empty_string(self, service):
        """Test building poster URL returns None when path is empty."""
        result = service._build_poster_url("")
        assert result is None

    def test_extract_year_valid_date(self, service):
        """Test extracting year from valid release date."""
        result = service._extract_year("1999-03-31")
        assert result == 1999

    def test_extract_year_with_none(self, service):
        """Test extracting year returns None when date is None."""
        result = service._extract_year(None)
        assert result is None

    def test_extract_year_with_empty_string(self, service):
        """Test extracting year returns None when date is empty."""
        result = service._extract_year("")
        assert result is None

    def test_extract_year_with_invalid_format(self, service):
        """Test extracting year returns None when date format is invalid."""
        result = service._extract_year("invalid")
        assert result is None

    def test_extract_year_with_short_string(self, service):
        """Test extracting year from short string extracts first 4 chars."""
        # The implementation takes first 4 chars, so "99" becomes 99
        result = service._extract_year("99")
        assert result == 99

    def test_extract_year_with_non_numeric_prefix(self, service):
        """Test extracting year returns None when prefix is non-numeric."""
        result = service._extract_year("abcd-01-01")
        assert result is None

    def test_parse_movie_result(self, service):
        """Test parsing a movie result from TMDB API response."""
        raw_movie = {
            "id": 603,
            "title": "The Matrix",
            "release_date": "1999-03-31",
            "poster_path": "/abc123.jpg",
            "overview": "A computer hacker learns about the true nature of reality.",
        }

        result = service._parse_movie_result(raw_movie)

        assert isinstance(result, TMDBMovieResult)
        assert result.tmdb_id == 603
        assert result.title == "The Matrix"
        assert result.year == 1999
        assert result.poster_path == "/abc123.jpg"
        assert result.poster_url == "https://image.tmdb.org/t/p/w185/abc123.jpg"
        assert result.overview == "A computer hacker learns about the true nature of reality."

    def test_parse_movie_result_with_missing_fields(self, service):
        """Test parsing a movie result with missing optional fields."""
        raw_movie = {
            "id": 12345,
            "title": "Mystery Movie",
        }

        result = service._parse_movie_result(raw_movie)

        assert result.tmdb_id == 12345
        assert result.title == "Mystery Movie"
        assert result.year is None
        assert result.poster_path is None
        assert result.poster_url is None
        assert result.overview is None

    def test_parse_movie_result_with_empty_overview(self, service):
        """Test parsing a movie result with empty overview string."""
        raw_movie = {
            "id": 12345,
            "title": "No Overview Movie",
            "overview": "",
        }

        result = service._parse_movie_result(raw_movie)

        assert result.overview is None


class TestTMDBServiceContextManager:
    """Tests for TMDBService context manager behavior."""

    @pytest.mark.asyncio
    async def test_context_manager_creates_client(self):
        """Test that entering context creates HTTP client."""
        with patch("app.services.tmdb.settings") as mock_settings:
            mock_settings.TMDB_API_KEY = "test-api-key"
            mock_settings.TMDB_BASE_URL = "https://api.themoviedb.org/3"
            mock_settings.TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w185"

            service = TMDBService()
            assert service._client is None

            async with service as s:
                assert s._client is not None
                assert isinstance(s._client, httpx.AsyncClient)

            assert service._client is None

    @pytest.mark.asyncio
    async def test_get_client_raises_without_context(self):
        """Test that _get_client raises error when not in context."""
        with patch("app.services.tmdb.settings") as mock_settings:
            mock_settings.TMDB_API_KEY = "test-api-key"
            mock_settings.TMDB_BASE_URL = "https://api.themoviedb.org/3"
            mock_settings.TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w185"

            service = TMDBService()

            with pytest.raises(RuntimeError) as exc_info:
                service._get_client()

            assert "must be used as an async context manager" in str(exc_info.value)


class TestTMDBServiceSearchMovies:
    """Tests for TMDBService.search_movies method."""

    @pytest.fixture
    def mock_settings(self):
        """Patch settings for all tests."""
        with patch("app.services.tmdb.settings") as mock:
            mock.TMDB_API_KEY = "test-api-key"
            mock.TMDB_BASE_URL = "https://api.themoviedb.org/3"
            mock.TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w185"
            yield mock

    @pytest.mark.asyncio
    async def test_search_movies_returns_results(self, mock_settings):
        """Test search_movies returns parsed results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "id": 603,
                    "title": "The Matrix",
                    "release_date": "1999-03-31",
                    "poster_path": "/abc123.jpg",
                    "overview": "A computer hacker learns about reality.",
                },
                {
                    "id": 604,
                    "title": "The Matrix Reloaded",
                    "release_date": "2003-05-15",
                    "poster_path": "/def456.jpg",
                    "overview": "Neo fights to save humanity.",
                },
            ]
        }

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            async with TMDBService() as service:
                results = await service.search_movies("The Matrix")

            assert len(results) == 2
            assert results[0].tmdb_id == 603
            assert results[0].title == "The Matrix"
            assert results[0].year == 1999
            assert results[1].tmdb_id == 604
            assert results[1].title == "The Matrix Reloaded"
            assert results[1].year == 2003

    @pytest.mark.asyncio
    async def test_search_movies_with_year_filter(self, mock_settings):
        """Test search_movies includes year parameter when provided."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            async with TMDBService() as service:
                await service.search_movies("The Matrix", year=1999)

            # Verify the call was made with correct parameters
            call_args = mock_get.call_args
            assert "year" in call_args.kwargs["params"]
            assert call_args.kwargs["params"]["year"] == 1999

    @pytest.mark.asyncio
    async def test_search_movies_without_year_filter(self, mock_settings):
        """Test search_movies does not include year parameter when not provided."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            async with TMDBService() as service:
                await service.search_movies("The Matrix")

            call_args = mock_get.call_args
            assert "year" not in call_args.kwargs["params"]

    @pytest.mark.asyncio
    async def test_search_movies_empty_results(self, mock_settings):
        """Test search_movies returns empty list when no results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            async with TMDBService() as service:
                results = await service.search_movies("NonexistentMovie12345")

            assert results == []

    @pytest.mark.asyncio
    async def test_search_movies_rate_limit_error(self, mock_settings):
        """Test search_movies raises TMDBRateLimitError on 429 response."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "30"}

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            async with TMDBService() as service:
                with pytest.raises(TMDBRateLimitError) as exc_info:
                    await service.search_movies("The Matrix")

                assert "Rate limit exceeded" in str(exc_info.value)
                assert "30" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_movies_invalid_api_key(self, mock_settings):
        """Test search_movies raises TMDBAPIError on 401 response."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Invalid API key"

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            async with TMDBService() as service:
                with pytest.raises(TMDBAPIError) as exc_info:
                    await service.search_movies("The Matrix")

                assert "Invalid TMDB API key" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_movies_server_error(self, mock_settings):
        """Test search_movies raises TMDBAPIError on 500 response."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            async with TMDBService() as service:
                with pytest.raises(TMDBAPIError) as exc_info:
                    await service.search_movies("The Matrix")

                assert "status 500" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_movies_timeout_error(self, mock_settings):
        """Test search_movies raises TMDBServiceError on timeout."""
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Request timed out")

            async with TMDBService() as service:
                with pytest.raises(TMDBServiceError) as exc_info:
                    await service.search_movies("The Matrix")

                assert "timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_movies_connection_error(self, mock_settings):
        """Test search_movies raises TMDBServiceError on connection error."""
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.RequestError("Connection failed")

            async with TMDBService() as service:
                with pytest.raises(TMDBServiceError) as exc_info:
                    await service.search_movies("The Matrix")

                assert "Failed to connect" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_movies_uses_correct_url(self, mock_settings):
        """Test search_movies uses correct API endpoint."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            async with TMDBService() as service:
                await service.search_movies("Test")

            call_args = mock_get.call_args
            assert call_args[0][0] == "https://api.themoviedb.org/3/search/movie"

    @pytest.mark.asyncio
    async def test_search_movies_includes_api_key(self, mock_settings):
        """Test search_movies includes API key in request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            async with TMDBService() as service:
                await service.search_movies("Test")

            call_args = mock_get.call_args
            assert call_args.kwargs["params"]["api_key"] == "test-api-key"


class TestConvenienceSearchFunction:
    """Tests for the convenience search_movies function."""

    @pytest.mark.asyncio
    async def test_search_movies_function(self):
        """Test the convenience search_movies function works correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "id": 603,
                    "title": "The Matrix",
                    "release_date": "1999-03-31",
                    "poster_path": "/abc123.jpg",
                    "overview": "A computer hacker.",
                },
            ]
        }

        with patch("app.services.tmdb.settings") as mock_settings:
            mock_settings.TMDB_API_KEY = "test-api-key"
            mock_settings.TMDB_BASE_URL = "https://api.themoviedb.org/3"
            mock_settings.TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w185"

            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_response

                results = await search_movies("The Matrix")

                assert len(results) == 1
                assert results[0].title == "The Matrix"

    @pytest.mark.asyncio
    async def test_search_movies_function_with_year(self):
        """Test the convenience search_movies function with year parameter."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}

        with patch("app.services.tmdb.settings") as mock_settings:
            mock_settings.TMDB_API_KEY = "test-api-key"
            mock_settings.TMDB_BASE_URL = "https://api.themoviedb.org/3"
            mock_settings.TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w185"

            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_response

                await search_movies("The Matrix", year=1999)

                call_args = mock_get.call_args
                assert call_args.kwargs["params"]["year"] == 1999
