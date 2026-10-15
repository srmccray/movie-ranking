"""Session endpoints for the Amazon Prime import workflow.

- POST /amazon-prime/upload/ - Upload CSV, parse, and match with TMDB
- GET /amazon-prime/session/{session_id}/ - Get current session state
- DELETE /amazon-prime/session/{session_id}/ - Cancel import session
"""

import logging

from fastapi import APIRouter, HTTPException, UploadFile, status

from app.database import DbSession
from app.dependencies import CurrentUser
from app.schemas.import_amazon import (
    ImportSessionDetailResponse,
    ImportSessionResponse,
    MatchedMovieItem,
)
from app.services.csv_parser import parse_amazon_prime_csv
from app.services.import_session import import_session_store

from .deps import get_session_or_404
from .matching import match_movies_with_tmdb

logger = logging.getLogger(__name__)

router = APIRouter()


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
    session = get_session_or_404(session_id, current_user)

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
    session = get_session_or_404(session_id, current_user)

    import_session_store.delete_session(session_id)
