"""Review endpoints for the Amazon Prime import workflow.

- POST /amazon-prime/session/{session_id}/movie/{index}/add/ - Add movie with rating
- POST /amazon-prime/session/{session_id}/movie/{index}/skip/ - Skip movie
- PATCH /amazon-prime/session/{session_id}/movie/{index}/match/ - Update movie's TMDB match
"""

import logging
from datetime import date

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.database import DbSession
from app.dependencies import CurrentUser
from app.models.movie import Movie
from app.models.ranking import Ranking
from app.schemas.import_amazon import (
    ImportMovieAddRequest,
    ImportMovieMatchRequest,
    MatchedMovieItem,
)
from app.schemas.ranking import RankingResponse
from app.services.tmdb import get_movie_details
from app.utils.time import to_naive_utc, utc_now_naive

from .deps import check_index, get_pending_movie, get_session_or_404

logger = logging.getLogger(__name__)

router = APIRouter()


def parse_release_date(release_date_str: str | None) -> date | None:
    """Parse a TMDB release date string (YYYY-MM-DD) to a date object.

    Args:
        release_date_str: Date string in YYYY-MM-DD format, or None.

    Returns:
        Parsed date object, or None if invalid/missing.
    """
    if not release_date_str:
        return None
    try:
        return date.fromisoformat(release_date_str)
    except ValueError:
        return None


@router.post(
    "/amazon-prime/session/{session_id}/movie/{index}/add/",
    response_model=RankingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add movie from import session",
    responses={
        201: {"description": "Movie added to rankings"},
        400: {"description": "Movie has no TMDB match or already processed"},
        401: {"description": "Not authenticated"},
        404: {"description": "Session or movie not found"},
    },
)
async def add_import_movie(
    session_id: str,
    index: int,
    request: ImportMovieAddRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> Ranking:
    """Add a movie from the import session to user's rankings.

    Creates the movie in the database if it doesn't exist, then creates
    a ranking for the user.

    Args:
        session_id: The unique import session ID.
        index: Index of the movie in the session (0-based).
        request: Rating data (rating 1-5, optional rated_at).
        current_user: The authenticated user (from JWT token).
        db: Async database session.

    Returns:
        The created ranking.

    Raises:
        HTTPException: 400 if movie has no TMDB match or already processed.
        HTTPException: 404 if session or movie index not found.
    """
    session = get_session_or_404(session_id, current_user)

    movie_data = get_pending_movie(session, index)

    if movie_data.tmdb_match is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add movie without TMDB match",
        )

    # Get or create movie in database
    tmdb_id = movie_data.tmdb_match.tmdb_id
    result = await db.execute(select(Movie).where(Movie.tmdb_id == tmdb_id))
    movie = result.scalar_one_or_none()

    if movie is None:
        # Fetch runtime from TMDB details API
        runtime = None
        try:
            details = await get_movie_details(tmdb_id)
            runtime = details.runtime
        except Exception as e:
            logger.warning(f"Failed to fetch TMDB details for {tmdb_id}: {e}")

        # Create new movie with full TMDB data
        movie = Movie(
            tmdb_id=tmdb_id,
            title=movie_data.tmdb_match.title,
            year=movie_data.tmdb_match.year,
            poster_url=movie_data.tmdb_match.poster_url,
            genre_ids=movie_data.tmdb_match.genre_ids,
            vote_average=movie_data.tmdb_match.vote_average,
            vote_count=movie_data.tmdb_match.vote_count,
            release_date=parse_release_date(movie_data.tmdb_match.release_date),
            original_language=movie_data.tmdb_match.original_language,
            runtime=runtime,
        )
        db.add(movie)
        await db.flush()
        await db.refresh(movie)
    else:
        # Update existing movie if it's missing metadata
        needs_update = False
        if movie.genre_ids is None and movie_data.tmdb_match.genre_ids:
            movie.genre_ids = movie_data.tmdb_match.genre_ids
            needs_update = True
        if movie.vote_average is None and movie_data.tmdb_match.vote_average is not None:
            movie.vote_average = movie_data.tmdb_match.vote_average
            needs_update = True
        if movie.vote_count is None and movie_data.tmdb_match.vote_count is not None:
            movie.vote_count = movie_data.tmdb_match.vote_count
            needs_update = True
        if movie.release_date is None and movie_data.tmdb_match.release_date:
            movie.release_date = parse_release_date(movie_data.tmdb_match.release_date)
            needs_update = True
        if movie.original_language is None and movie_data.tmdb_match.original_language:
            movie.original_language = movie_data.tmdb_match.original_language
            needs_update = True
        if movie.runtime is None:
            try:
                details = await get_movie_details(tmdb_id)
                if details.runtime:
                    movie.runtime = details.runtime
                    needs_update = True
            except Exception as e:
                logger.warning(f"Failed to fetch TMDB details for {tmdb_id}: {e}")

        if needs_update:
            await db.flush()
            await db.refresh(movie)

    # Determine rated_at: use request value, fall back to watch_date, then now
    rated_at = to_naive_utc(request.rated_at)
    if rated_at is None and movie_data.parsed.watch_date:
        rated_at = to_naive_utc(movie_data.parsed.watch_date)
    if rated_at is None:
        rated_at = utc_now_naive()

    # Check if user already has a ranking for this movie (upsert pattern)
    existing_result = await db.execute(
        select(Ranking).where(
            Ranking.user_id == current_user.id,
            Ranking.movie_id == movie.id,
        )
    )
    existing_ranking = existing_result.scalar_one_or_none()

    if existing_ranking is not None:
        # Update existing ranking
        existing_ranking.rating = request.rating
        existing_ranking.rated_at = rated_at
        await db.flush()
        await db.refresh(existing_ranking)
        ranking = existing_ranking
    else:
        # Create new ranking
        ranking = Ranking(
            user_id=current_user.id,
            movie_id=movie.id,
            rating=request.rating,
            rated_at=rated_at,
        )
        db.add(ranking)
        await db.flush()
        await db.refresh(ranking)

    # Update session state
    session.movies[index]["status"] = "added"
    session.added_count += 1
    session.current_index = index + 1

    return ranking


@router.post(
    "/amazon-prime/session/{session_id}/movie/{index}/skip/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Skip movie in import session",
    responses={
        204: {"description": "Movie skipped"},
        400: {"description": "Movie already processed"},
        401: {"description": "Not authenticated"},
        404: {"description": "Session or movie not found"},
    },
)
async def skip_import_movie(
    session_id: str,
    index: int,
    current_user: CurrentUser,
) -> None:
    """Skip a movie in the import session.

    Args:
        session_id: The unique import session ID.
        index: Index of the movie in the session (0-based).
        current_user: The authenticated user (from JWT token).

    Raises:
        HTTPException: 400 if movie already processed.
        HTTPException: 404 if session or movie index not found.
    """
    session = get_session_or_404(session_id, current_user)

    movie_data = get_pending_movie(session, index)

    # Update session state
    session.movies[index]["status"] = "skipped"
    session.skipped_count += 1
    session.current_index = index + 1


@router.patch(
    "/amazon-prime/session/{session_id}/movie/{index}/match/",
    response_model=MatchedMovieItem,
    summary="Update movie match in import session",
    responses={
        200: {"description": "Movie match updated successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Session or movie not found"},
    },
)
async def update_import_movie_match(
    session_id: str,
    index: int,
    request: ImportMovieMatchRequest,
    current_user: CurrentUser,
) -> MatchedMovieItem:
    """Update the TMDB match for a movie in the import session.

    Used when a user manually searches and selects a different movie match.
    Sets confidence to 1.0 (user-selected) and clears alternatives.
    Status remains 'pending' so user can still add or skip.

    Args:
        session_id: The unique import session ID.
        index: Index of the movie in the session (0-based).
        request: New TMDB match data (tmdb_id, title, year, poster_url, overview).
        current_user: The authenticated user (from JWT token).

    Returns:
        The updated MatchedMovieItem with the new match.

    Raises:
        HTTPException: 404 if session or movie index not found.
    """
    session = get_session_or_404(session_id, current_user)

    check_index(session, index)

    # Update the movie's match in the session with full TMDB data
    session.movies[index]["tmdb_match"] = {
        "tmdb_id": request.tmdb_id,
        "title": request.title,
        "year": request.year,
        "poster_url": request.poster_url,
        "overview": request.overview,
        "genre_ids": request.genre_ids,
        "vote_average": request.vote_average,
        "vote_count": request.vote_count,
        "release_date": request.release_date,
        "original_language": request.original_language,
    }
    session.movies[index]["confidence"] = 1.0  # User-selected
    session.movies[index]["alternatives"] = []  # Clear alternatives
    # Keep status as 'pending' so user can still add/skip

    return MatchedMovieItem(**session.movies[index])
