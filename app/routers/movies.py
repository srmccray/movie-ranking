"""Movies router for creating and managing movies."""

import logging

from fastapi import APIRouter, HTTPException, Query, status

from app.database import DbSession
from app.dependencies import CurrentUser
from app.models.movie import Movie
from app.schemas.movie import (
    MovieCreate,
    MovieResponse,
    TMDBSearchResponse,
    TMDBSearchResult,
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

        # Convert to response schema
        search_results = [
            TMDBSearchResult(
                tmdb_id=result.tmdb_id,
                title=result.title,
                year=result.year,
                poster_url=result.poster_url,
                overview=result.overview,
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
        201: {"description": "Movie created successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
async def create_movie(
    movie_data: MovieCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> Movie:
    """Add a new movie to the database.

    Requires authentication. Any authenticated user can add movies.

    Args:
        movie_data: Movie data containing title, optional year, tmdb_id, and poster_url.
        current_user: The authenticated user (from JWT token).
        db: Async database session.

    Returns:
        The created movie with id, title, year, tmdb_id, poster_url, and created_at.

    Raises:
        HTTPException: 401 Unauthorized if not authenticated.
    """
    new_movie = Movie(
        title=movie_data.title,
        year=movie_data.year,
        tmdb_id=movie_data.tmdb_id,
        poster_url=movie_data.poster_url,
    )

    db.add(new_movie)
    await db.flush()
    await db.refresh(new_movie)

    return new_movie
