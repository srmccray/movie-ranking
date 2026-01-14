"""Rankings router for creating and listing user movie rankings."""

from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.database import DbSession
from app.dependencies import CurrentUser
from app.models.movie import Movie
from app.models.ranking import Ranking
from app.schemas.ranking import (
    RankingCreate,
    RankingListResponse,
    RankingResponse,
    RankingWithMovie,
)

router = APIRouter(tags=["rankings"])


def to_naive_utc(dt: datetime | None) -> datetime | None:
    """Convert a datetime to naive UTC datetime for database storage."""
    if dt is None:
        return None
    # If timezone-aware, convert to UTC and remove tzinfo
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


@router.post(
    "/",
    response_model=RankingResponse,
    summary="Create or update a ranking",
    responses={
        200: {"description": "Ranking updated successfully"},
        201: {"description": "Ranking created successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Movie not found"},
        422: {"description": "Validation error"},
    },
)
async def create_or_update_ranking(
    ranking_data: RankingCreate,
    current_user: CurrentUser,
    db: DbSession,
    response: Response,
) -> Ranking:
    """Create or update a ranking for a movie.

    If the user has already ranked this movie, the rating is updated.
    Otherwise, a new ranking is created.

    Args:
        ranking_data: Ranking data containing movie_id and rating.
        current_user: The authenticated user (from JWT token).
        db: Async database session.
        response: FastAPI response object for setting status code.

    Returns:
        The created or updated ranking.

    Raises:
        HTTPException: 401 Unauthorized if not authenticated.
        HTTPException: 404 Not Found if movie does not exist.
    """
    # Check if movie exists
    movie_result = await db.execute(
        select(Movie).where(Movie.id == ranking_data.movie_id)
    )
    movie = movie_result.scalar_one_or_none()

    if movie is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found",
        )

    # Check if user already has a ranking for this movie
    existing_result = await db.execute(
        select(Ranking).where(
            Ranking.user_id == current_user.id,
            Ranking.movie_id == ranking_data.movie_id,
        )
    )
    existing_ranking = existing_result.scalar_one_or_none()

    if existing_ranking is not None:
        # Update existing ranking
        existing_ranking.rating = ranking_data.rating
        # Only update rated_at if explicitly provided
        if ranking_data.rated_at is not None:
            existing_ranking.rated_at = to_naive_utc(ranking_data.rated_at)
        await db.flush()
        await db.refresh(existing_ranking)
        response.status_code = status.HTTP_200_OK
        return existing_ranking
    else:
        # Create new ranking
        new_ranking = Ranking(
            user_id=current_user.id,
            movie_id=ranking_data.movie_id,
            rating=ranking_data.rating,
            rated_at=to_naive_utc(ranking_data.rated_at) or datetime.utcnow(),
        )
        db.add(new_ranking)
        await db.flush()
        await db.refresh(new_ranking)
        response.status_code = status.HTTP_201_CREATED
        return new_ranking


@router.get(
    "/",
    response_model=RankingListResponse,
    summary="List user's rankings",
    responses={
        200: {"description": "Rankings retrieved successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def list_rankings(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: Literal["rated_at", "rating", "title", "year"] = Query(
        default="rated_at",
        description="Field to sort by",
    ),
    sort_order: Literal["asc", "desc"] = Query(
        default="desc",
        description="Sort order (asc or desc)",
    ),
) -> RankingListResponse:
    """List all movies the authenticated user has ranked.

    Returns paginated results with configurable sorting.

    Args:
        current_user: The authenticated user (from JWT token).
        db: Async database session.
        limit: Number of results to return (1-100, default 20).
        offset: Number of results to skip (default 0).
        sort_by: Field to sort by (rated_at, rating, title, year).
        sort_order: Sort order (asc or desc).

    Returns:
        Paginated list of rankings with embedded movie details.

    Raises:
        HTTPException: 401 Unauthorized if not authenticated.
    """
    # Get total count of user's rankings
    count_result = await db.execute(
        select(func.count()).where(Ranking.user_id == current_user.id)
    )
    total = count_result.scalar_one()

    # Build query with sorting
    query = (
        select(Ranking)
        .options(joinedload(Ranking.movie))
        .where(Ranking.user_id == current_user.id)
    )

    # Determine sort column
    if sort_by == "rated_at":
        sort_column = Ranking.rated_at
    elif sort_by == "rating":
        sort_column = Ranking.rating
    elif sort_by == "title":
        sort_column = Movie.title
    elif sort_by == "year":
        sort_column = Movie.year
    else:
        sort_column = Ranking.rated_at

    # Apply sort order
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    # Execute with pagination
    rankings_result = await db.execute(query.limit(limit).offset(offset))
    rankings = rankings_result.scalars().unique().all()

    # Convert to response schema
    items = [RankingWithMovie.model_validate(ranking) for ranking in rankings]

    return RankingListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.delete(
    "/{ranking_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a ranking",
    responses={
        204: {"description": "Ranking deleted successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to delete this ranking"},
        404: {"description": "Ranking not found"},
    },
)
async def delete_ranking(
    ranking_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """Delete a ranking by ID.

    Users can only delete their own rankings.

    Args:
        ranking_id: UUID of the ranking to delete.
        current_user: The authenticated user (from JWT token).
        db: Async database session.

    Raises:
        HTTPException: 401 if not authenticated.
        HTTPException: 403 if ranking belongs to another user.
        HTTPException: 404 if ranking not found.
    """
    # Find the ranking
    result = await db.execute(select(Ranking).where(Ranking.id == ranking_id))
    ranking = result.scalar_one_or_none()

    if ranking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ranking not found",
        )

    # Check ownership
    if ranking.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this ranking",
        )

    await db.delete(ranking)
    await db.flush()
