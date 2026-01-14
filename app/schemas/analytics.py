"""Analytics schemas for activity and insights responses."""

from datetime import date as date_type
from typing import List

from pydantic import BaseModel, Field


class ActivityDay(BaseModel):
    """Schema for a single day's activity.

    Attributes:
        date: The date of the activity.
        count: Number of movies rated on this day.
    """

    date: date_type = Field(..., description="Date of activity")
    count: int = Field(..., ge=0, description="Number of movies rated")


class ActivityResponse(BaseModel):
    """Schema for activity chart response.

    RESPONSE SHAPE: { activity: [...], start_date: "...", end_date: "..." }

    Attributes:
        activity: List of days with activity (days with 0 activity are omitted).
        start_date: Start of the date range.
        end_date: End of the date range.
    """

    activity: List[ActivityDay] = Field(
        ..., description="List of days with activity"
    )
    start_date: date_type = Field(..., description="Start of date range")
    end_date: date_type = Field(..., description="End of date range")


class GenreStats(BaseModel):
    """Schema for genre statistics.

    Attributes:
        genre_id: TMDB genre ID.
        genre_name: Human-readable genre name.
        count: Number of movies rated in this genre.
        average_rating: Average user rating for movies in this genre.
    """

    genre_id: int = Field(..., description="TMDB genre ID")
    genre_name: str = Field(..., description="Genre name")
    count: int = Field(..., ge=0, description="Number of movies rated")
    average_rating: float = Field(..., ge=0, le=5, description="Average rating")


class GenreResponse(BaseModel):
    """Schema for genre distribution response.

    RESPONSE SHAPE: { genres: [...], total_movies: N }

    Attributes:
        genres: List of genre statistics, sorted by count descending.
        total_movies: Total number of rated movies in the period.
    """

    genres: List[GenreStats] = Field(
        ..., description="Genre statistics sorted by count"
    )
    total_movies: int = Field(..., ge=0, description="Total movies rated")
