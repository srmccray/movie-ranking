"""Shared helpers for rolling-year genre analytics."""

from collections import defaultdict
from datetime import date
from uuid import UUID

from sqlalchemy import Date, cast, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.ranking import Ranking


def rolling_year_window(today: date) -> tuple[date, date]:
    """Return (start, end) for the rolling year: first of this month last year to today."""
    return date(today.year - 1, today.month, 1), today


async def fetch_year_rankings(
    db: AsyncSession, user_id: UUID, start_date: date, end_date: date
) -> list[Ranking]:
    """Fetch a user's rankings (with movies) rated within [start_date, end_date]."""
    result = await db.execute(
        select(Ranking)
        .options(joinedload(Ranking.movie))
        .where(
            Ranking.user_id == user_id,
            cast(Ranking.rated_at, Date) >= start_date,
            cast(Ranking.rated_at, Date) <= end_date,
        )
    )
    return list(result.scalars().unique().all())


def primary_genre_counts(
    rankings: list[Ranking],
) -> tuple[dict[int, int], dict[int, list[int]]]:
    """Count rankings and collect ratings by each movie's primary (first) genre."""
    counts: dict[int, int] = defaultdict(int)
    ratings: dict[int, list[int]] = defaultdict(list)
    for ranking in rankings:
        if ranking.movie and ranking.movie.genre_ids:
            genre_id = ranking.movie.genre_ids[0]
            counts[genre_id] += 1
            ratings[genre_id].append(ranking.rating)
    return counts, ratings
