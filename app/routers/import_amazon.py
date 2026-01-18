"""Amazon Prime import router for CSV upload and movie import workflow.

This router handles the multi-step import workflow for importing watch history
from Amazon Prime Video CSV exports.

Endpoints:
- POST /amazon-prime/upload/ - Upload CSV, parse, and match with TMDB
- GET /amazon-prime/session/{session_id}/ - Get current session state
- POST /amazon-prime/session/{session_id}/movie/{index}/add/ - Add movie with rating
- POST /amazon-prime/session/{session_id}/movie/{index}/skip/ - Skip movie
- PATCH /amazon-prime/session/{session_id}/movie/{index}/match/ - Update movie's TMDB match
- DELETE /amazon-prime/session/{session_id}/ - Cancel import session
"""

import asyncio
import logging
from datetime import date, datetime, timezone
from difflib import SequenceMatcher
from uuid import UUID

from fastapi import APIRouter, HTTPException, UploadFile, status
from sqlalchemy import select

from app.database import DbSession
from app.dependencies import CurrentUser
from app.models.movie import Movie
from app.models.ranking import Ranking
from app.schemas.import_amazon import (
    ImportMovieAddRequest,
    ImportMovieMatchRequest,
    ImportSessionDetailResponse,
    ImportSessionResponse,
    MatchedMovieItem,
    ParsedMovieItem,
    TMDBMatchResult,
)
from app.schemas.ranking import RankingResponse
from app.services.csv_parser import parse_amazon_prime_csv
from app.services.import_session import import_session_store
from app.services.tmdb import TMDBRateLimitError, TMDBService, get_movie_details

logger = logging.getLogger(__name__)

router = APIRouter(tags=["import"])


def to_naive_utc(dt: datetime | None) -> datetime | None:
    """Convert a datetime to naive UTC datetime for database storage.

    See root CLAUDE.md for datetime handling strategy.
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


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


def calculate_confidence(
    parsed_title: str,
    parsed_year: int | None,
    tmdb_title: str,
    tmdb_year: int | None,
) -> float:
    """Calculate match confidence score (0.0 - 1.0).

    Uses title similarity (60% weight) and year match (40% weight).

    Args:
        parsed_title: Title from Amazon Prime CSV.
        parsed_year: Year extracted from watch date (optional).
        tmdb_title: Title from TMDB search result.
        tmdb_year: Release year from TMDB (optional).

    Returns:
        Confidence score between 0.0 and 1.0.
    """
    score = 0.0

    # Title similarity (0.0 - 0.6)
    title_ratio = SequenceMatcher(
        None,
        parsed_title.lower(),
        tmdb_title.lower(),
    ).ratio()
    score += title_ratio * 0.6

    # Year match (0.0 - 0.4)
    if parsed_year and tmdb_year:
        if parsed_year == tmdb_year:
            score += 0.4
        elif abs(parsed_year - tmdb_year) == 1:
            score += 0.2  # Off by one year, still likely correct

    return min(score, 1.0)


async def match_movies_with_tmdb(
    parsed_movies: list,
    user_id: UUID,
    db: DbSession,
) -> tuple[list[MatchedMovieItem], int]:
    """Match parsed movies against TMDB with rate limiting.

    Args:
        parsed_movies: List of ParsedMovie objects from CSV parser.
        user_id: Current user's ID for checking existing rankings.
        db: Database session.

    Returns:
        Tuple of (matched movies list, already_ranked count).
    """
    matched: list[MatchedMovieItem] = []
    already_ranked = 0

    # Get user's existing ranked movie TMDB IDs
    existing_result = await db.execute(
        select(Movie.tmdb_id)
        .join(Ranking, Ranking.movie_id == Movie.id)
        .where(Ranking.user_id == user_id)
    )
    existing_tmdb_ids = set(row[0] for row in existing_result.all())

    async with TMDBService() as service:
        for i, movie in enumerate(parsed_movies):
            try:
                # Rate limiting: delay every 35 requests
                if i > 0 and i % 35 == 0:
                    await asyncio.sleep(1.0)

                results = await service.search_movies(
                    query=movie.title,
                    year=movie.year,
                )

                if results:
                    best_match = results[0]
                    confidence = calculate_confidence(
                        movie.title,
                        movie.year,
                        best_match.title,
                        best_match.year,
                    )

                    # Check if already ranked
                    if best_match.tmdb_id in existing_tmdb_ids:
                        already_ranked += 1
                        continue  # Skip already-ranked movies

                    matched.append(
                        MatchedMovieItem(
                            parsed=ParsedMovieItem(
                                title=movie.title,
                                watch_date=movie.watch_date,
                                prime_image_url=movie.prime_image_url,
                            ),
                            tmdb_match=TMDBMatchResult(
                                tmdb_id=best_match.tmdb_id,
                                title=best_match.title,
                                year=best_match.year,
                                poster_url=best_match.poster_url,
                                overview=best_match.overview,
                                genre_ids=best_match.genre_ids,
                                vote_average=best_match.vote_average,
                                vote_count=best_match.vote_count,
                                release_date=best_match.release_date,
                                original_language=best_match.original_language,
                            ),
                            confidence=confidence,
                            alternatives=[
                                TMDBMatchResult(
                                    tmdb_id=r.tmdb_id,
                                    title=r.title,
                                    year=r.year,
                                    poster_url=r.poster_url,
                                    overview=r.overview,
                                    genre_ids=r.genre_ids,
                                    vote_average=r.vote_average,
                                    vote_count=r.vote_count,
                                    release_date=r.release_date,
                                    original_language=r.original_language,
                                )
                                for r in results[1:3]  # Up to 2 alternatives
                            ],
                            status="pending",
                        )
                    )
                else:
                    # No TMDB match found
                    matched.append(
                        MatchedMovieItem(
                            parsed=ParsedMovieItem(
                                title=movie.title,
                                watch_date=movie.watch_date,
                                prime_image_url=movie.prime_image_url,
                            ),
                            tmdb_match=None,
                            confidence=0.0,
                            alternatives=[],
                            status="pending",
                        )
                    )

            except TMDBRateLimitError:
                # Wait and retry once
                logger.warning(f"Rate limited on movie {i}, waiting 2 seconds...")
                await asyncio.sleep(2.0)
                try:
                    results = await service.search_movies(query=movie.title)
                    if results:
                        best_match = results[0]
                        if best_match.tmdb_id not in existing_tmdb_ids:
                            matched.append(
                                MatchedMovieItem(
                                    parsed=ParsedMovieItem(
                                        title=movie.title,
                                        watch_date=movie.watch_date,
                                        prime_image_url=movie.prime_image_url,
                                    ),
                                    tmdb_match=TMDBMatchResult(
                                        tmdb_id=best_match.tmdb_id,
                                        title=best_match.title,
                                        year=best_match.year,
                                        poster_url=best_match.poster_url,
                                        overview=best_match.overview,
                                        genre_ids=best_match.genre_ids,
                                        vote_average=best_match.vote_average,
                                        vote_count=best_match.vote_count,
                                        release_date=best_match.release_date,
                                        original_language=best_match.original_language,
                                    ),
                                    confidence=calculate_confidence(
                                        movie.title,
                                        movie.year,
                                        best_match.title,
                                        best_match.year,
                                    ),
                                    alternatives=[],
                                    status="pending",
                                )
                            )
                        else:
                            already_ranked += 1
                    else:
                        matched.append(
                            MatchedMovieItem(
                                parsed=ParsedMovieItem(
                                    title=movie.title,
                                    watch_date=movie.watch_date,
                                    prime_image_url=movie.prime_image_url,
                                ),
                                tmdb_match=None,
                                confidence=0.0,
                                alternatives=[],
                                status="pending",
                            )
                        )
                except TMDBRateLimitError:
                    # Still rate limited, mark as unmatched
                    matched.append(
                        MatchedMovieItem(
                            parsed=ParsedMovieItem(
                                title=movie.title,
                                watch_date=movie.watch_date,
                                prime_image_url=movie.prime_image_url,
                            ),
                            tmdb_match=None,
                            confidence=0.0,
                            alternatives=[],
                            status="pending",
                        )
                    )

            except Exception as e:
                logger.error(f"Error matching movie '{movie.title}': {e}")
                matched.append(
                    MatchedMovieItem(
                        parsed=ParsedMovieItem(
                            title=movie.title,
                            watch_date=movie.watch_date,
                            prime_image_url=movie.prime_image_url,
                        ),
                        tmdb_match=None,
                        confidence=0.0,
                        alternatives=[],
                        status="pending",
                    )
                )

    return matched, already_ranked


@router.post(
    "/amazon-prime/upload/",
    response_model=ImportSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Amazon Prime CSV file",
    responses={
        201: {"description": "Import session created successfully"},
        400: {"description": "Invalid CSV file"},
        401: {"description": "Not authenticated"},
    },
)
async def upload_amazon_prime_csv(
    file: UploadFile,
    current_user: CurrentUser,
    db: DbSession,
) -> ImportSessionResponse:
    """Upload and parse an Amazon Prime Video watch history CSV file.

    Parses the CSV, matches movies against TMDB, and creates an import session
    for the user to review and add movies to their rankings.

    Args:
        file: The uploaded CSV file.
        current_user: The authenticated user (from JWT token).
        db: Async database session.

    Returns:
        ImportSessionResponse with session ID and matched movies.

    Raises:
        HTTPException: 400 if file is not a CSV or parsing fails.
        HTTPException: 401 if not authenticated.
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV file",
        )

    # Parse CSV
    parse_result = parse_amazon_prime_csv(file.file)

    if parse_result.total_entries == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file is empty or could not be parsed",
        )

    if parse_result.movies_found == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No movies found in CSV file (only TV shows?)",
        )

    # Match movies with TMDB
    matched_movies, already_ranked = await match_movies_with_tmdb(
        parse_result.movies,
        current_user.id,
        db,
    )

    # Create session
    session_id = import_session_store.create_session(
        user_id=str(current_user.id),
        movies=[m.model_dump() for m in matched_movies],
        total_entries=parse_result.total_entries,
        movies_found=parse_result.movies_found,
        tv_shows_filtered=parse_result.tv_shows_filtered,
        already_ranked=already_ranked,
    )

    return ImportSessionResponse(
        session_id=session_id,
        total_entries=parse_result.total_entries,
        movies_found=parse_result.movies_found,
        tv_shows_filtered=parse_result.tv_shows_filtered,
        already_ranked=already_ranked,
        ready_for_review=len(matched_movies),
        movies=matched_movies,
    )


@router.get(
    "/amazon-prime/session/{session_id}/",
    response_model=ImportSessionDetailResponse,
    summary="Get import session details",
    responses={
        200: {"description": "Session retrieved successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Session not found or expired"},
    },
)
async def get_import_session(
    session_id: str,
    current_user: CurrentUser,
) -> ImportSessionDetailResponse:
    """Get the current state of an import session.

    Args:
        session_id: The unique import session ID.
        current_user: The authenticated user (from JWT token).

    Returns:
        ImportSessionDetailResponse with session state and movies.

    Raises:
        HTTPException: 404 if session not found or expired.
    """
    session = import_session_store.get_session(session_id, str(current_user.id))

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import session not found or expired",
        )

    movies = [MatchedMovieItem(**m) for m in session.movies]
    pending_count = sum(1 for m in movies if m.status == "pending")

    return ImportSessionDetailResponse(
        session_id=session_id,
        current_index=session.current_index,
        total_movies=len(movies),
        added_count=session.added_count,
        skipped_count=session.skipped_count,
        remaining_count=pending_count,
        movies=movies,
    )


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
    session = import_session_store.get_session(session_id, str(current_user.id))

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import session not found or expired",
        )

    if index < 0 or index >= len(session.movies):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie index out of range",
        )

    movie_data = MatchedMovieItem(**session.movies[index])

    if movie_data.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Movie has already been processed",
        )

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
        rated_at = datetime.utcnow()

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
    session = import_session_store.get_session(session_id, str(current_user.id))

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import session not found or expired",
        )

    if index < 0 or index >= len(session.movies):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie index out of range",
        )

    movie_data = MatchedMovieItem(**session.movies[index])

    if movie_data.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Movie has already been processed",
        )

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
    session = import_session_store.get_session(session_id, str(current_user.id))

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import session not found or expired",
        )

    if index < 0 or index >= len(session.movies):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie index out of range",
        )

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


@router.delete(
    "/amazon-prime/session/{session_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel import session",
    responses={
        204: {"description": "Session cancelled"},
        401: {"description": "Not authenticated"},
        404: {"description": "Session not found"},
    },
)
async def cancel_import_session(
    session_id: str,
    current_user: CurrentUser,
) -> None:
    """Cancel and delete an import session.

    Args:
        session_id: The unique import session ID.
        current_user: The authenticated user (from JWT token).

    Raises:
        HTTPException: 404 if session not found.
    """
    session = import_session_store.get_session(session_id, str(current_user.id))

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import session not found or expired",
        )

    import_session_store.delete_session(session_id)
