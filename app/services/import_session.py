"""Import session storage service for Amazon Prime import workflow.

This module provides in-memory session storage for the multi-step import
workflow. Sessions are temporary and will be lost on server restart,
which is acceptable for the MVP implementation.

Session Pattern:
- One session per user (new upload replaces existing session)
- Sessions expire after 30 minutes (TTL)
- Maximum 500 movies per session
- User ownership enforced on all session access
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


@dataclass
class ImportSession:
    """Represents an active import session.

    Attributes:
        user_id: UUID string of the user who owns this session.
        movies: List of MatchedMovieItem dicts for the review workflow.
        created_at: When the session was created (naive UTC).
        current_index: Current position in the review queue.
        added_count: Number of movies added to rankings.
        skipped_count: Number of movies skipped by user.
        total_entries: Total CSV rows parsed.
        movies_found: Number of movie entries (vs TV shows).
        tv_shows_filtered: Number of TV series filtered out.
        already_ranked: Number of movies already in user's rankings.
    """

    user_id: str
    movies: list[dict[str, Any]]
    created_at: datetime
    current_index: int = 0
    added_count: int = 0
    skipped_count: int = 0
    total_entries: int = 0
    movies_found: int = 0
    tv_shows_filtered: int = 0
    already_ranked: int = 0


class ImportSessionStore:
    """In-memory store for import sessions with automatic cleanup.

    This store manages import sessions for the Amazon Prime import
    workflow. It enforces:
    - One session per user (replacement on new upload)
    - 30-minute TTL for sessions
    - 500 movie limit per session
    - User ownership validation

    Example:
        store = ImportSessionStore()

        # Create a session
        session_id = store.create_session(
            user_id="user-uuid",
            movies=[...],
            total_entries=100,
            movies_found=80,
            tv_shows_filtered=20,
            already_ranked=5,
        )

        # Get a session
        session = store.get_session(session_id, user_id="user-uuid")
        if session:
            # Process session data
            pass

        # Delete a session
        store.delete_session(session_id)
    """

    SESSION_TTL_MINUTES = 30
    MAX_MOVIES_PER_SESSION = 500

    def __init__(self) -> None:
        """Initialize the session store with empty session maps."""
        self._sessions: dict[str, ImportSession] = {}
        self._user_sessions: dict[str, str] = {}  # user_id -> session_id mapping

    def create_session(
        self,
        user_id: str,
        movies: list[dict[str, Any]],
        total_entries: int,
        movies_found: int,
        tv_shows_filtered: int,
        already_ranked: int,
    ) -> str:
        """Create a new import session, replacing any existing session for this user.

        Args:
            user_id: UUID string of the user creating the session.
            movies: List of MatchedMovieItem dicts to include in the session.
            total_entries: Total number of CSV rows parsed.
            movies_found: Number of movie entries identified.
            tv_shows_filtered: Number of TV series entries filtered out.
            already_ranked: Number of movies already in user's rankings.

        Returns:
            The unique session ID for this import session.

        Note:
            If the user already has an active session, it will be deleted
            and replaced with this new session. Movies list is truncated
            to MAX_MOVIES_PER_SESSION (500) if it exceeds the limit.
        """
        import uuid

        # Remove existing session for this user (replacement policy)
        if user_id in self._user_sessions:
            old_session_id = self._user_sessions[user_id]
            self._sessions.pop(old_session_id, None)

        # Generate unique session ID
        session_id = str(uuid.uuid4())

        # Truncate movies list to max limit
        truncated_movies = movies[: self.MAX_MOVIES_PER_SESSION]

        # Create new session
        self._sessions[session_id] = ImportSession(
            user_id=user_id,
            movies=truncated_movies,
            created_at=datetime.utcnow(),
            total_entries=total_entries,
            movies_found=movies_found,
            tv_shows_filtered=tv_shows_filtered,
            already_ranked=already_ranked,
        )
        self._user_sessions[user_id] = session_id

        return session_id

    def get_session(self, session_id: str, user_id: str) -> ImportSession | None:
        """Get a session if it exists, belongs to the user, and hasn't expired.

        Args:
            session_id: The unique session ID to retrieve.
            user_id: The user ID requesting the session (for ownership check).

        Returns:
            The ImportSession if valid and owned by user, None otherwise.

        Note:
            This method automatically deletes expired sessions when accessed.
            Returns None if:
            - Session doesn't exist
            - Session belongs to a different user
            - Session has expired (TTL exceeded)
        """
        session = self._sessions.get(session_id)
        if session is None:
            return None

        # Check ownership
        if session.user_id != user_id:
            return None

        # Check expiry
        now = datetime.utcnow()
        if now - session.created_at > timedelta(minutes=self.SESSION_TTL_MINUTES):
            self.delete_session(session_id)
            return None

        return session

    def update_session(
        self,
        session_id: str,
        user_id: str,
        **updates: Any,
    ) -> ImportSession | None:
        """Update session fields and return the updated session.

        Args:
            session_id: The unique session ID to update.
            user_id: The user ID requesting the update (for ownership check).
            **updates: Keyword arguments for fields to update.
                       Valid fields: current_index, added_count, skipped_count, movies

        Returns:
            The updated ImportSession if successful, None if session not found or unauthorized.

        Example:
            updated = store.update_session(
                session_id,
                user_id,
                added_count=session.added_count + 1,
                current_index=session.current_index + 1,
            )
        """
        session = self.get_session(session_id, user_id)
        if session is None:
            return None

        # Update allowed fields
        allowed_fields = {"current_index", "added_count", "skipped_count", "movies"}
        for key, value in updates.items():
            if key in allowed_fields:
                setattr(session, key, value)

        return session

    def delete_session(self, session_id: str) -> None:
        """Delete a session by ID.

        Args:
            session_id: The unique session ID to delete.

        Note:
            This also removes the user-to-session mapping.
            Safe to call even if session doesn't exist.
        """
        session = self._sessions.pop(session_id, None)
        if session:
            self._user_sessions.pop(session.user_id, None)

    def cleanup_expired(self) -> int:
        """Remove all expired sessions from the store.

        Returns:
            The number of sessions that were removed.

        Note:
            This can be called periodically to prevent memory buildup.
            Each get_session() call also cleans up individual expired sessions.
        """
        now = datetime.utcnow()
        expired = [
            sid
            for sid, session in self._sessions.items()
            if now - session.created_at > timedelta(minutes=self.SESSION_TTL_MINUTES)
        ]
        for sid in expired:
            self.delete_session(sid)
        return len(expired)

    def get_session_count(self) -> int:
        """Get the current number of active sessions.

        Returns:
            The number of sessions currently in the store.
        """
        return len(self._sessions)


# Global session store instance for use by routers
import_session_store = ImportSessionStore()
