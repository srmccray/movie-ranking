"""Movies router for creating and managing movies."""

from fastapi import APIRouter, status

from app.database import DbSession
from app.dependencies import CurrentUser
from app.models.movie import Movie
from app.schemas.movie import MovieCreate, MovieResponse

router = APIRouter(tags=["movies"])


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
        movie_data: Movie data containing title and optional year.
        current_user: The authenticated user (from JWT token).
        db: Async database session.

    Returns:
        The created movie with id, title, year, and created_at.

    Raises:
        HTTPException: 401 Unauthorized if not authenticated.
    """
    new_movie = Movie(
        title=movie_data.title,
        year=movie_data.year,
    )

    db.add(new_movie)
    await db.flush()
    await db.refresh(new_movie)

    return new_movie
