"""Rankings router for creating and listing user movie rankings."""

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
) -> RankingListResponse:
    """List all movies the authenticated user has ranked.

    Returns paginated results ordered by updated_at descending (most recent first).

    Args:
        current_user: The authenticated user (from JWT token).
        db: Async database session.
        limit: Number of results to return (1-100, default 20).
        offset: Number of results to skip (default 0).

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

    # Get paginated rankings with movie details
    rankings_result = await db.execute(
        select(Ranking)
        .options(joinedload(Ranking.movie))
        .where(Ranking.user_id == current_user.id)
        .order_by(Ranking.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rankings = rankings_result.scalars().unique().all()

    # Convert to response schema
    items = [RankingWithMovie.model_validate(ranking) for ranking in rankings]

    return RankingListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )
