"""Movies router for creating and managing movies."""

import logging

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.database import DbSession
from app.dependencies import CurrentUser
from app.models.movie import Movie
from app.schemas.movie import (
    MovieCreate,
    MovieResponse,
    TMDBSearchResponse,
    TMDBSearchResult,
)
from app.services.movies import (
    MovieData,
    backfill_missing_metadata,
    create_movie as create_movie_record,
    find_movie_by_tmdb_id,
)
from app.services.tmdb import (
    TMDBAPIError,
    TMDBRateLimitError,
    TMDBService,
    TMDBServiceError,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["movies"])


@router.get(
    "/search/",
    response_model=TMDBSearchResponse,
    summary="Search movies on TMDB",
    responses={
        200: {"description": "Search results returned successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
        500: {"description": "TMDB service error"},
        503: {"description": "TMDB rate limit exceeded"},
    },
)
async def search_tmdb_movies(
    current_user: CurrentUser,
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    year: int | None = Query(None, ge=1888, le=2031, description="Filter by year"),
) -> TMDBSearchResponse:
    """Search for movies on The Movie Database (TMDB).

    Requires authentication. Searches TMDB for movies matching the query.

    Args:
        current_user: The authenticated user (from JWT token).
        q: Search query string (movie title).
        year: Optional year filter to narrow results.

    Returns:
        TMDBSearchResponse with list of matching movies.

    Raises:
        HTTPException: 401 Unauthorized if not authenticated.
        HTTPException: 503 Service Unavailable if TMDB rate limit exceeded.
        HTTPException: 500 Internal Server Error for other TMDB errors.
    """
    try:
        async with TMDBService() as service:
            results = await service.search_movies(query=q, year=year)

        # Convert to response schema with all metadata fields
        search_results = [
            TMDBSearchResult(
                tmdb_id=result.tmdb_id,
                title=result.title,
                year=result.year,
                poster_url=result.poster_url,
                overview=result.overview,
                genre_ids=result.genre_ids,
                vote_average=result.vote_average,
                vote_count=result.vote_count,
                release_date=result.release_date,
                original_language=result.original_language,
            )
            for result in results
        ]

        return TMDBSearchResponse(
            results=search_results,
            query=q,
            year=year,
        )

    except TMDBRateLimitError as e:
        logger.warning(f"TMDB rate limit exceeded: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TMDB rate limit exceeded. Please try again later.",
        )
    except TMDBAPIError as e:
        logger.error(f"TMDB API error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search TMDB. Please try again.",
        )
    except TMDBServiceError as e:
        logger.error(f"TMDB service error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="TMDB service unavailable. Please try again later.",
        )


@router.post(
    "/",
    response_model=MovieResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new movie",
    responses={
        200: {"description": "Movie with this TMDB id already exists; returned"},
        201: {"description": "Movie created successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
async def create_movie(
    movie_data: MovieCreate,
    response: Response,
    current_user: CurrentUser,
    db: DbSession,
) -> Movie:
    """Add a movie to the database (get-or-create by TMDB id).

    Requires authentication. Any authenticated user can add movies. When
    ``tmdb_id`` is set and a movie with that id exists, it is returned with
    HTTP 200 (NULL metadata fields are back-filled); otherwise a new movie is
    created with HTTP 201. Movies without ``tmdb_id`` are always created.

    Args:
        movie_data: Movie data containing title, year, tmdb_id, poster_url,
            and additional metadata fields (genre_ids, vote_average, etc.).
        response: Used to set the 200 status for an existing movie.
        current_user: The authenticated user (from JWT token).
        db: Async database session.

    Returns:
        The created or existing movie with all fields and timestamps.

    Raises:
        HTTPException: 401 Unauthorized if not authenticated.
    """
    data = MovieData(**movie_data.model_dump())

    if data.tmdb_id is not None:
        existing = await find_movie_by_tmdb_id(db, data.tmdb_id)
        if existing is not None:
            if backfill_missing_metadata(existing, data):
                await db.flush()
                await db.refresh(existing)
            response.status_code = status.HTTP_200_OK
            return existing

    return await create_movie_record(db, data)
