"""Shared checks for the Amazon Prime import review and session endpoints."""

from fastapi import HTTPException, status

from app.dependencies import CurrentUser
from app.schemas.import_amazon import MatchedMovieItem
from app.services.import_session import ImportSession, import_session_store

SESSION_NOT_FOUND_DETAIL = "Import session not found or expired"
INDEX_OUT_OF_RANGE_DETAIL = "Movie index out of range"
ALREADY_PROCESSED_DETAIL = "Movie has already been processed"


def get_session_or_404(session_id: str, user: CurrentUser) -> ImportSession:
    """Return the user's import session or raise 404."""
    session = import_session_store.get_session(session_id, str(user.id))
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=SESSION_NOT_FOUND_DETAIL,
        )
    return session


def check_index(session: ImportSession, index: int) -> None:
    """Raise 404 if index is outside the session's movie list."""
    if index < 0 or index >= len(session.movies):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=INDEX_OUT_OF_RANGE_DETAIL,
        )


def get_pending_movie(session: ImportSession, index: int) -> MatchedMovieItem:
    """Return the movie at index; 404 if out of range, 400 if not pending."""
    check_index(session, index)
    movie = MatchedMovieItem(**session.movies[index])
    if movie.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ALREADY_PROCESSED_DETAIL,
        )
    return movie
