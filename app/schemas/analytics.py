"""Analytics schemas for activity and insights responses."""

from datetime import date as date_type
from typing import List, Optional

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


class StatsResponse(BaseModel):
    """Schema for user stats summary response.

    RESPONSE SHAPE: { total_movies: N, total_watch_time_minutes: N, average_rating: N, current_streak: N, longest_streak: N, top_genre: "..." }

    Attributes:
        total_movies: Total number of movies rated by the user.
        total_watch_time_minutes: Total runtime of all rated movies in minutes.
        average_rating: Average rating across all movies (0-5).
        current_streak: Current consecutive days with ratings.
        longest_streak: Longest streak of consecutive days ever.
        top_genre: The user's most-rated genre name, or None if no ratings.
    """

    total_movies: int = Field(..., ge=0, description="Total movies rated by user")
    total_watch_time_minutes: int = Field(
        ..., ge=0, description="Total runtime of all rated movies in minutes"
    )
    average_rating: float = Field(..., ge=0, le=5, description="Average rating (0-5)")
    current_streak: int = Field(
        ..., ge=0, description="Current consecutive days with ratings"
    )
    longest_streak: int = Field(
        ..., ge=0, description="Longest streak of consecutive days ever"
    )
    top_genre: Optional[str] = Field(
        None, description="User's most-rated genre name, or None if no ratings"
    )


class RatingCount(BaseModel):
    """Schema for a single rating value count.

    Attributes:
        rating: Rating value (1-5).
        count: Number of movies with this rating.
    """

    rating: int = Field(..., ge=1, le=5, description="Rating value (1-5)")
    count: int = Field(..., ge=0, description="Number of movies with this rating")


class RatingDistributionResponse(BaseModel):
    """Schema for rating distribution response.

    RESPONSE SHAPE: { distribution: [...], total: N }

    Returns the count of movies for each rating value (1-5).
    All five rating values are always included, even if count is 0.

    Attributes:
        distribution: List of counts for each rating value (1-5).
        total: Total number of rated movies.
    """

    distribution: List[RatingCount] = Field(
        ..., description="Counts for each rating value 1-5"
    )
    total: int = Field(..., ge=0, description="Total rated movies")
