"""Movie schemas for request/response validation."""

from datetime import datetime
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
    """

    title: str = Field(..., min_length=1, max_length=500)
    year: Optional[int] = Field(None, ge=1888, le=2031)
    tmdb_id: Optional[int] = Field(None, description="TMDB movie ID")
    poster_url: Optional[str] = Field(
        None, max_length=500, description="URL to movie poster image"
    )


class MovieResponse(BaseModel):
    """Schema for movie response with full details.

    Attributes:
        id: Unique movie identifier.
        title: Movie title.
        year: Release year (optional).
        tmdb_id: TMDB movie ID (optional).
        poster_url: URL to movie poster image (optional).
        created_at: Record creation timestamp.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    year: Optional[int]
    tmdb_id: Optional[int]
    poster_url: Optional[str]
    created_at: datetime


class MovieBrief(BaseModel):
    """Abbreviated movie schema for embedding in ranking responses.

    Attributes:
        id: Unique movie identifier.
        title: Movie title.
        year: Release year (optional).
        poster_url: URL to movie poster image (optional).
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    year: Optional[int]
    poster_url: Optional[str]


class TMDBSearchResult(BaseModel):
    """Schema for a single TMDB movie search result.

    Attributes:
        tmdb_id: TMDB movie ID.
        title: Movie title.
        year: Release year extracted from release_date (optional).
        poster_url: Full URL to movie poster thumbnail (optional).
        overview: Movie synopsis/description (optional).
    """

    tmdb_id: int = Field(..., description="TMDB movie ID")
    title: str = Field(..., description="Movie title")
    year: Optional[int] = Field(None, description="Release year")
    poster_url: Optional[str] = Field(None, description="URL to movie poster")
    overview: Optional[str] = Field(None, description="Movie synopsis")


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
