"""Ranking schemas for request/response validation."""

from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.movie import MovieBrief


class RankingCreate(BaseModel):
    """Schema for creating or updating a ranking.

    Attributes:
        movie_id: UUID of the movie to rank.
        rating: Rating value (1-5).
    """

    movie_id: UUID
    rating: int = Field(..., ge=1, le=5)


class RankingResponse(BaseModel):
    """Schema for ranking response with full details.

    Attributes:
        id: Unique ranking identifier.
        movie_id: UUID of the ranked movie.
        rating: Rating value (1-5).
        created_at: Initial ranking timestamp.
        updated_at: Last update timestamp.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    movie_id: UUID
    rating: int
    created_at: datetime
    updated_at: datetime


class RankingWithMovie(BaseModel):
    """Schema for ranking with embedded movie details.

    Used in list endpoint to include movie information.

    Attributes:
        id: Unique ranking identifier.
        rating: Rating value (1-5).
        created_at: Initial ranking timestamp.
        updated_at: Last update timestamp.
        movie: Embedded movie details.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rating: int
    created_at: datetime
    updated_at: datetime
    movie: MovieBrief


class RankingListResponse(BaseModel):
    """Schema for paginated ranking list response.

    Attributes:
        items: List of rankings with movie details.
        total: Total number of rankings for this user.
        limit: Number of results requested.
        offset: Number of results skipped.
    """

    items: List[RankingWithMovie]
    total: int
    limit: int
    offset: int
