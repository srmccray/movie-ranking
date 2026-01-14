"""Movie schemas for request/response validation."""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MovieCreate(BaseModel):
    """Schema for creating a new movie.

    Attributes:
        title: Movie title (1-500 characters).
        year: Release year (optional, 1888-2031).
        tmdb_id: TMDB movie ID (optional).
        poster_url: URL to movie poster image (optional).
        genre_ids: List of TMDB genre IDs (optional).
        vote_average: TMDB user rating 0.0-10.0 (optional).
        vote_count: Number of TMDB votes (optional).
        release_date: Full release date (optional).
        original_language: ISO 639-1 language code (optional).
        runtime: Movie length in minutes (optional).
    """

    title: str = Field(..., min_length=1, max_length=500)
    year: Optional[int] = Field(None, ge=1888, le=2031)
    tmdb_id: Optional[int] = Field(None, description="TMDB movie ID")
    poster_url: Optional[str] = Field(
        None, max_length=500, description="URL to movie poster image"
    )
    genre_ids: Optional[list[int]] = Field(
        None, description="List of TMDB genre IDs"
    )
    vote_average: Optional[float] = Field(
        None, ge=0.0, le=10.0, description="TMDB user rating"
    )
    vote_count: Optional[int] = Field(
        None, ge=0, description="Number of TMDB votes"
    )
    release_date: Optional[date] = Field(
        None, description="Full release date"
    )
    original_language: Optional[str] = Field(
        None, max_length=10, description="ISO 639-1 language code"
    )
    runtime: Optional[int] = Field(
        None, ge=0, description="Movie length in minutes"
    )


class MovieResponse(BaseModel):
    """Schema for movie response with full details.

    Attributes:
        id: Unique movie identifier.
        title: Movie title.
        year: Release year (optional).
        tmdb_id: TMDB movie ID (optional).
        poster_url: URL to movie poster image (optional).
        genre_ids: List of TMDB genre IDs (optional).
        vote_average: TMDB user rating 0.0-10.0 (optional).
        vote_count: Number of TMDB votes (optional).
        release_date: Full release date (optional).
        original_language: ISO 639-1 language code (optional).
        runtime: Movie length in minutes (optional).
        created_at: Record creation timestamp.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    year: Optional[int]
    tmdb_id: Optional[int]
    poster_url: Optional[str]
    genre_ids: Optional[list[int]]
    vote_average: Optional[float]
    vote_count: Optional[int]
    release_date: Optional[date]
    original_language: Optional[str]
    runtime: Optional[int]
    created_at: datetime


class MovieBrief(BaseModel):
    """Abbreviated movie schema for embedding in ranking responses.

    Attributes:
        id: Unique movie identifier.
        title: Movie title.
        year: Release year (optional).
        poster_url: URL to movie poster image (optional).
        genre_ids: List of TMDB genre IDs (optional).
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    year: Optional[int]
    poster_url: Optional[str]
    genre_ids: Optional[list[int]]


class TMDBSearchResult(BaseModel):
    """Schema for a single TMDB movie search result.

    Attributes:
        tmdb_id: TMDB movie ID.
        title: Movie title.
        year: Release year extracted from release_date (optional).
        poster_url: Full URL to movie poster thumbnail (optional).
        overview: Movie synopsis/description (optional).
        genre_ids: List of TMDB genre IDs (optional).
        vote_average: TMDB user rating 0.0-10.0 (optional).
        vote_count: Number of TMDB votes (optional).
        release_date: Full release date string (optional).
        original_language: ISO 639-1 language code (optional).
    """

    tmdb_id: int = Field(..., description="TMDB movie ID")
    title: str = Field(..., description="Movie title")
    year: Optional[int] = Field(None, description="Release year")
    poster_url: Optional[str] = Field(None, description="URL to movie poster")
    overview: Optional[str] = Field(None, description="Movie synopsis")
    genre_ids: Optional[list[int]] = Field(None, description="List of TMDB genre IDs")
    vote_average: Optional[float] = Field(None, description="TMDB user rating")
    vote_count: Optional[int] = Field(None, description="Number of TMDB votes")
    release_date: Optional[str] = Field(None, description="Full release date (YYYY-MM-DD)")
    original_language: Optional[str] = Field(None, description="ISO 639-1 language code")


class TMDBSearchResponse(BaseModel):
    """Schema for TMDB search response with list of results.

    Attributes:
        results: List of movies matching the search query.
        query: The original search query.
        year: The year filter used (if any).
    """

    results: list[TMDBSearchResult] = Field(
        ..., description="List of matching movies"
    )
    query: str = Field(..., description="The search query")
    year: Optional[int] = Field(None, description="Year filter used")


class TMDBMovieDetails(BaseModel):
    """Schema for TMDB movie details response.

    Used to fetch additional data like runtime that isn't in search results.

    Attributes:
        tmdb_id: TMDB movie ID.
        runtime: Movie length in minutes (optional).
    """

    tmdb_id: int = Field(..., description="TMDB movie ID")
    runtime: Optional[int] = Field(None, description="Movie length in minutes")


class GenreResponse(BaseModel):
    """Schema for genre response.

    Attributes:
        id: TMDB genre ID.
        name: Genre name.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
