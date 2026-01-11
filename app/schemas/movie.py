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
    """

    title: str = Field(..., min_length=1, max_length=500)
    year: Optional[int] = Field(None, ge=1888, le=2031)


class MovieResponse(BaseModel):
    """Schema for movie response with full details.

    Attributes:
        id: Unique movie identifier.
        title: Movie title.
        year: Release year (optional).
        created_at: Record creation timestamp.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    year: Optional[int]
    created_at: datetime


class MovieBrief(BaseModel):
    """Abbreviated movie schema for embedding in ranking responses.

    Attributes:
        id: Unique movie identifier.
        title: Movie title.
        year: Release year (optional).
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    year: Optional[int]
