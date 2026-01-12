"""TMDB API service for movie search integration.

This module provides async functions to search for movies using
The Movie Database (TMDB) API.
"""

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# HTTP client timeout configuration
TMDB_TIMEOUT = 10.0  # seconds


@dataclass
class TMDBMovieResult:
    """Result from TMDB movie search.

    Attributes:
        tmdb_id: The movie's ID in TMDB.
        title: The movie title.
        year: Release year extracted from release_date (optional).
        poster_path: Relative path to poster image (optional).
        poster_url: Full URL to poster thumbnail (optional).
        overview: Movie synopsis/description (optional).
    """

    tmdb_id: int
    title: str
    year: int | None
    poster_path: str | None
    poster_url: str | None
    overview: str | None


class TMDBServiceError(Exception):
    """Base exception for TMDB service errors."""

    pass


class TMDBRateLimitError(TMDBServiceError):
    """Raised when TMDB rate limit is exceeded."""

    pass


class TMDBAPIError(TMDBServiceError):
    """Raised when TMDB API returns an error response."""

    pass


class TMDBService:
    """Async service for interacting with TMDB API.

    This service handles HTTP calls to TMDB, including error handling
    and rate limiting.

    Example:
        async with TMDBService() as service:
            results = await service.search_movies("The Matrix", year=1999)
    """

    def __init__(self) -> None:
        """Initialize the TMDB service with configuration."""
        self.api_key = settings.TMDB_API_KEY
        self.base_url = settings.TMDB_BASE_URL
        self.image_base_url = settings.TMDB_IMAGE_BASE_URL
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "TMDBService":
        """Enter async context and create HTTP client."""
        self._client = httpx.AsyncClient(
            timeout=TMDB_TIMEOUT,
            headers={"Accept": "application/json"},
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context and close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        """Get the HTTP client, raising error if not in context."""
        if self._client is None:
            raise RuntimeError(
                "TMDBService must be used as an async context manager"
            )
        return self._client

    def _build_poster_url(self, poster_path: str | None) -> str | None:
        """Build full poster URL from relative path.

        Args:
            poster_path: Relative path from TMDB (e.g., "/abc123.jpg").

        Returns:
            Full URL to the poster image, or None if no path provided.
        """
        if not poster_path:
            return None
        return f"{self.image_base_url}{poster_path}"

    def _extract_year(self, release_date: str | None) -> int | None:
        """Extract year from TMDB release_date string.

        Args:
            release_date: Date string in "YYYY-MM-DD" format.

        Returns:
            Year as integer, or None if invalid/missing.
        """
        if not release_date:
            return None
        try:
            return int(release_date[:4])
        except (ValueError, IndexError):
            return None

    def _parse_movie_result(self, movie: dict[str, Any]) -> TMDBMovieResult:
        """Parse a single movie result from TMDB response.

        Args:
            movie: Raw movie dict from TMDB API.

        Returns:
            Parsed TMDBMovieResult dataclass.
        """
        poster_path = movie.get("poster_path")
        return TMDBMovieResult(
            tmdb_id=movie["id"],
            title=movie["title"],
            year=self._extract_year(movie.get("release_date")),
            poster_path=poster_path,
            poster_url=self._build_poster_url(poster_path),
            overview=movie.get("overview") or None,
        )

    async def search_movies(
        self,
        query: str,
        year: int | None = None,
    ) -> list[TMDBMovieResult]:
        """Search for movies by title.

        Args:
            query: Search query string (movie title).
            year: Optional year filter to narrow results.

        Returns:
            List of TMDBMovieResult objects.

        Raises:
            TMDBRateLimitError: If TMDB rate limit is exceeded.
            TMDBAPIError: If TMDB returns an error response.
            TMDBServiceError: For other service-related errors.
        """
        client = self._get_client()

        params: dict[str, Any] = {
            "api_key": self.api_key,
            "query": query,
            "include_adult": "false",
            "language": "en-US",
            "page": 1,
        }

        if year is not None:
            params["year"] = year

        try:
            response = await client.get(
                f"{self.base_url}/search/movie",
                params=params,
            )

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "unknown")
                logger.warning(f"TMDB rate limit exceeded. Retry after: {retry_after}")
                raise TMDBRateLimitError(
                    f"Rate limit exceeded. Retry after {retry_after} seconds."
                )

            if response.status_code == 401:
                logger.error("TMDB API authentication failed - check API key")
                raise TMDBAPIError("Invalid TMDB API key")

            if response.status_code != 200:
                logger.error(
                    f"TMDB API error: {response.status_code} - {response.text}"
                )
                raise TMDBAPIError(
                    f"TMDB API returned status {response.status_code}"
                )

            data = response.json()
            results = data.get("results", [])

            return [self._parse_movie_result(movie) for movie in results]

        except httpx.TimeoutException:
            logger.error("TMDB API request timed out")
            raise TMDBServiceError("TMDB API request timed out")
        except httpx.RequestError as e:
            logger.error(f"TMDB API request failed: {e}")
            raise TMDBServiceError(f"Failed to connect to TMDB: {e}")


async def search_movies(
    query: str,
    year: int | None = None,
) -> list[TMDBMovieResult]:
    """Convenience function to search movies without managing context.

    This creates a new HTTP client for each call. For multiple calls,
    prefer using TMDBService as a context manager.

    Args:
        query: Search query string (movie title).
        year: Optional year filter to narrow results.

    Returns:
        List of TMDBMovieResult objects.
    """
    async with TMDBService() as service:
        return await service.search_movies(query, year)
