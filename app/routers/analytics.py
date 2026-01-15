"""Analytics router for user activity and insights."""

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import func, select, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession
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
    RatingCount,
    RatingDistributionResponse,
    StatsResponse,
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


def _calculate_streaks(rating_dates: list[date]) -> tuple[int, int]:
    """Calculate current and longest streaks from a list of rating dates.

    A streak is consecutive days with at least one rating. The current streak
    is valid if the last rating was today or yesterday.

    Args:
        rating_dates: List of unique dates when ratings occurred, sorted ascending.

    Returns:
        Tuple of (current_streak, longest_streak).
    """
    if not rating_dates:
        return 0, 0

    today = date.today()
    yesterday = today - timedelta(days=1)

    # Sort dates and remove duplicates (already unique from query, but ensure)
    unique_dates = sorted(set(rating_dates))

    longest_streak = 1
    current_streak_count = 1

    # Calculate longest streak
    for i in range(1, len(unique_dates)):
        if unique_dates[i] - unique_dates[i - 1] == timedelta(days=1):
            current_streak_count += 1
            longest_streak = max(longest_streak, current_streak_count)
        else:
            current_streak_count = 1

    # Calculate current streak (must include today or yesterday)
    last_date = unique_dates[-1]
    if last_date != today and last_date != yesterday:
        # Streak is broken - last rating was more than 1 day ago
        return 0, longest_streak

    # Count backwards from the last date to find current streak
    current_streak = 1
    for i in range(len(unique_dates) - 2, -1, -1):
        if unique_dates[i + 1] - unique_dates[i] == timedelta(days=1):
            current_streak += 1
        else:
            break

    return current_streak, longest_streak


async def _get_top_genre(db: AsyncSession, user_id) -> str | None:
    """Get the user's most-rated genre for the rolling year.

    Counts movies by their primary genre (first genre_id in the array) and
    returns the genre name with the highest count. On ties, returns the
    genre that comes first alphabetically.

    Only considers ratings from the past rolling year to match the
    genre distribution chart.

    Args:
        db: Async database session.
        user_id: The user's ID.

    Returns:
        The genre name string, or None if the user has no ratings in the period.
    """
    today = date.today()
    start_date = date(today.year - 1, today.month, 1)
    end_date = today

    # Query rankings with movies for the rolling year
    result = await db.execute(
        select(Ranking)
        .options(joinedload(Ranking.movie))
        .where(
            Ranking.user_id == user_id,
            cast(Ranking.rated_at, Date) >= start_date,
            cast(Ranking.rated_at, Date) <= end_date,
        )
    )
    rankings = result.scalars().unique().all()

    if not rankings:
        return None

    # Count by primary genre (first genre in list)
    genre_counts: dict[int, int] = defaultdict(int)

    for ranking in rankings:
        if ranking.movie and ranking.movie.genre_ids:
            genre_id = ranking.movie.genre_ids[0]
            genre_counts[genre_id] += 1

    if not genre_counts:
        return None

    # Find max count
    max_count = max(genre_counts.values())

    # Get all genres with max count, convert to names
    top_genres_with_names = []
    for genre_id, count in genre_counts.items():
        if count == max_count:
            genre_name = GENRE_MAP.get(genre_id, f"Unknown ({genre_id})")
            top_genres_with_names.append(genre_name)

    # Sort alphabetically and return first (handles ties)
    top_genres_with_names.sort()
    return top_genres_with_names[0]


@router.get(
    "/stats/",
    response_model=StatsResponse,
    summary="Get user stats summary",
    responses={
        200: {"description": "Stats data retrieved successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def get_stats(
    current_user: CurrentUser,
    db: DbSession,
) -> StatsResponse:
    """Get summary statistics for the authenticated user.

    Returns aggregate statistics including total movies rated, total watch time,
    average rating, rating streaks, and top genre.

    Args:
        current_user: The authenticated user (from JWT token).
        db: Async database session.

    Returns:
        StatsResponse with user statistics. Returns zeros for users with no ratings.
    """
    # Query 1: Total movies and average rating
    stats_result = await db.execute(
        select(
            func.count(Ranking.id).label("total_movies"),
            func.coalesce(func.avg(Ranking.rating), 0).label("average_rating"),
        ).where(Ranking.user_id == current_user.id)
    )
    stats_row = stats_result.one()
    total_movies = stats_row.total_movies
    average_rating = round(float(stats_row.average_rating), 2)

    # Query 2: Total watch time (join with Movie, exclude null runtime)
    watch_time_result = await db.execute(
        select(func.coalesce(func.sum(Movie.runtime), 0).label("total_runtime"))
        .select_from(Ranking)
        .join(Movie, Ranking.movie_id == Movie.id)
        .where(
            Ranking.user_id == current_user.id,
            Movie.runtime.isnot(None),
        )
    )
    total_watch_time_minutes = watch_time_result.scalar_one()

    # Query 3: Get all unique rating dates for streak calculation
    dates_result = await db.execute(
        select(cast(Ranking.rated_at, Date).label("rating_date"))
        .where(Ranking.user_id == current_user.id)
        .group_by(cast(Ranking.rated_at, Date))
        .order_by(cast(Ranking.rated_at, Date))
    )
    rating_dates = [row.rating_date for row in dates_result.all()]

    # Calculate streaks
    current_streak, longest_streak = _calculate_streaks(rating_dates)

    # Query 4: Get top genre (most-rated genre by count)
    top_genre = await _get_top_genre(db, current_user.id)

    return StatsResponse(
        total_movies=total_movies,
        total_watch_time_minutes=total_watch_time_minutes,
        average_rating=average_rating,
        current_streak=current_streak,
        longest_streak=longest_streak,
        top_genre=top_genre,
    )


@router.get(
    "/rating-distribution/",
    response_model=RatingDistributionResponse,
    summary="Get rating distribution",
    responses={
        200: {"description": "Rating distribution retrieved successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def get_rating_distribution(
    current_user: CurrentUser,
    db: DbSession,
) -> RatingDistributionResponse:
    """Get rating distribution for the authenticated user.

    Returns the count of movies for each rating value (1-5).
    All five rating values are always included, even if count is 0.

    Args:
        current_user: The authenticated user (from JWT token).
        db: Async database session.

    Returns:
        RatingDistributionResponse with distribution counts and total.
    """
    # Query rating counts grouped by rating value
    result = await db.execute(
        select(
            Ranking.rating,
            func.count(Ranking.id).label("count"),
        )
        .where(Ranking.user_id == current_user.id)
        .group_by(Ranking.rating)
    )
    rows = result.all()

    # Convert to dict for easy lookup
    rating_counts = {row.rating: row.count for row in rows}

    # Build distribution with all 5 rating values (1-5)
    distribution = [
        RatingCount(rating=rating, count=rating_counts.get(rating, 0))
        for rating in range(1, 6)
    ]

    # Calculate total
    total = sum(rc.count for rc in distribution)

    return RatingDistributionResponse(
        distribution=distribution,
        total=total,
    )
