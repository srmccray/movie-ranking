"""Analytics router for user activity and insights."""

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import func, select, cast, Date
from sqlalchemy.orm import joinedload

from app.database import DbSession
from app.dependencies import CurrentUser
from app.models.movie import Movie
from app.models.ranking import Ranking
from app.schemas.analytics import (
    ActivityDay,
    ActivityResponse,
    GenreResponse,
    GenreStats,
)

router = APIRouter(tags=["analytics"])

# TMDB genre ID to name mapping
GENRE_MAP: dict[int, str] = {
    28: "Action",
    12: "Adventure",
    16: "Animation",
    35: "Comedy",
    80: "Crime",
    99: "Documentary",
    18: "Drama",
    10751: "Family",
    14: "Fantasy",
    36: "History",
    27: "Horror",
    10402: "Music",
    9648: "Mystery",
    10749: "Romance",
    878: "Sci-Fi",
    10770: "TV Movie",
    53: "Thriller",
    10752: "War",
    37: "Western",
}


@router.get(
    "/activity/",
    response_model=ActivityResponse,
    summary="Get user activity",
    responses={
        200: {"description": "Activity data retrieved successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def get_activity(
    current_user: CurrentUser,
    db: DbSession,
) -> ActivityResponse:
    """Get daily activity counts for the rolling year.

    Returns the number of movies rated per day for the past year
    through the end of the current month, suitable for rendering
    a GitHub-style activity chart.

    Args:
        current_user: The authenticated user (from JWT token).
        db: Async database session.

    Returns:
        ActivityResponse with list of days that have activity.
    """
    today = date.today()

    # Start from 1 year ago (rolling year), first of that month
    rolling_start = date(today.year - 1, today.month, 1)
    # Adjust to beginning of that week (Sunday)
    # weekday(): Mon=0, Sun=6, so (weekday+1)%7 gives days to subtract
    start_date = rolling_start - timedelta(days=(rolling_start.weekday() + 1) % 7)

    # End at the last day of the current month (include future dates)
    if today.month == 12:
        end_date = date(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(today.year, today.month + 1, 1) - timedelta(days=1)

    # Query daily activity counts
    result = await db.execute(
        select(
            cast(Ranking.rated_at, Date).label("date"),
            func.count(Ranking.id).label("count"),
        )
        .where(
            Ranking.user_id == current_user.id,
            cast(Ranking.rated_at, Date) >= start_date,
            cast(Ranking.rated_at, Date) <= end_date,
        )
        .group_by(cast(Ranking.rated_at, Date))
        .order_by(cast(Ranking.rated_at, Date))
    )

    rows = result.all()

    # Convert to response format
    activity = [
        ActivityDay(date=row.date, count=row.count)
        for row in rows
    ]

    return ActivityResponse(
        activity=activity,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/genres/",
    response_model=GenreResponse,
    summary="Get genre distribution",
    responses={
        200: {"description": "Genre data retrieved successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def get_genres(
    current_user: CurrentUser,
    db: DbSession,
) -> GenreResponse:
    """Get genre distribution statistics for the rolling year.

    Returns the count and average rating for each genre
    for the past year, suitable for rendering a genre distribution chart.

    Args:
        current_user: The authenticated user (from JWT token).
        db: Async database session.

    Returns:
        GenreResponse with genre statistics sorted by count.
    """
    today = date.today()

    # Rolling year: from 1 year ago to today
    start_date = date(today.year - 1, today.month, 1)
    end_date = today

    # Query rankings with movies for the year
    result = await db.execute(
        select(Ranking)
        .options(joinedload(Ranking.movie))
        .where(
            Ranking.user_id == current_user.id,
            cast(Ranking.rated_at, Date) >= start_date,
            cast(Ranking.rated_at, Date) <= end_date,
        )
    )
    rankings = result.scalars().unique().all()

    # Aggregate by primary genre (first genre in list, most relevant per TMDB)
    genre_counts: dict[int, int] = defaultdict(int)
    genre_ratings: dict[int, list[int]] = defaultdict(list)

    for ranking in rankings:
        if ranking.movie and ranking.movie.genre_ids:
            # Use only the first/primary genre
            genre_id = ranking.movie.genre_ids[0]
            genre_counts[genre_id] += 1
            genre_ratings[genre_id].append(ranking.rating)

    # Build genre stats
    genres: list[GenreStats] = []
    for genre_id, count in genre_counts.items():
        genre_name = GENRE_MAP.get(genre_id, f"Unknown ({genre_id})")
        ratings = genre_ratings[genre_id]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0.0

        genres.append(
            GenreStats(
                genre_id=genre_id,
                genre_name=genre_name,
                count=count,
                average_rating=round(avg_rating, 1),
            )
        )

    # Sort by count descending
    genres.sort(key=lambda g: g.count, reverse=True)

    return GenreResponse(
        genres=genres,
        total_movies=len(rankings),
    )
