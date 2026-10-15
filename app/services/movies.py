"""Movie persistence helpers shared by the movies and import routers."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movie import Movie


@dataclass(frozen=True)
class MovieData:
    """Movie fields used to create a movie or back-fill an existing one."""

    title: str
    year: int | None = None
    tmdb_id: int | None = None
    poster_url: str | None = None
    genre_ids: list[int] | None = None
    vote_average: float | None = None
    vote_count: int | None = None
    release_date: date | None = None
    original_language: str | None = None
    runtime: int | None = None


async def find_movie_by_tmdb_id(db: AsyncSession, tmdb_id: int) -> Movie | None:
    """Return the oldest movie with the given TMDB id, or None.

    Ordered by ``created_at`` then ``id`` so pre-existing duplicate rows
    never raise ``MultipleResultsFound``.
    """
    result = await db.execute(
        select(Movie)
        .where(Movie.tmdb_id == tmdb_id)
        .order_by(Movie.created_at, Movie.id)
        .limit(1)
    )
    return result.scalars().first()


async def create_movie(db: AsyncSession, data: MovieData) -> Movie:
    """Insert a new movie and return it with database defaults loaded."""
    movie = Movie(
        title=data.title,
        year=data.year,
        tmdb_id=data.tmdb_id,
        poster_url=data.poster_url,
        genre_ids=data.genre_ids,
        vote_average=data.vote_average,
        vote_count=data.vote_count,
        release_date=data.release_date,
        original_language=data.original_language,
        runtime=data.runtime,
    )
    db.add(movie)
    await db.flush()
    await db.refresh(movie)
    return movie


def backfill_missing_metadata(movie: Movie, data: MovieData) -> bool:
    """Fill only the NULL metadata fields of ``movie`` from ``data``.

    Returns True when at least one field changed (caller flushes/refreshes).
    """
    changed = False
    if movie.genre_ids is None and data.genre_ids:
        movie.genre_ids = data.genre_ids
        changed = True
    if movie.vote_average is None and data.vote_average is not None:
        movie.vote_average = data.vote_average
        changed = True
    if movie.vote_count is None and data.vote_count is not None:
        movie.vote_count = data.vote_count
        changed = True
    if movie.release_date is None and data.release_date:
        movie.release_date = data.release_date
        changed = True
    if movie.original_language is None and data.original_language:
        movie.original_language = data.original_language
        changed = True
    if movie.runtime is None and data.runtime:
        movie.runtime = data.runtime
        changed = True
    return changed
