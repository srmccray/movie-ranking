"""Tests for import session storage service.

These tests verify the ImportSessionStore functionality including:
- Session creation with unique IDs
- User ownership enforcement
- Session expiry after 30 minutes
- Session replacement when user starts new import
- 500 movie limit per session
- Session update and deletion
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from app.services.import_session import (
    ImportSession,
    ImportSessionStore,
    import_session_store,
)


class TestImportSession:
    """Tests for ImportSession dataclass."""

    def test_session_creation_with_required_fields(self):
        """Test creating a session with required fields."""
        movies = [{"title": "The Matrix", "status": "pending"}]
        session = ImportSession(
            user_id="user-123",
            movies=movies,
            created_at=datetime.utcnow(),
        )

        assert session.user_id == "user-123"
        assert session.movies == movies
        assert session.current_index == 0
        assert session.added_count == 0
        assert session.skipped_count == 0
        assert session.total_entries == 0
        assert session.movies_found == 0
        assert session.tv_shows_filtered == 0
        assert session.already_ranked == 0

    def test_session_creation_with_all_fields(self):
        """Test creating a session with all fields specified."""
        movies = [{"title": "The Matrix"}]
        created_at = datetime.utcnow()
        session = ImportSession(
            user_id="user-456",
            movies=movies,
            created_at=created_at,
            current_index=5,
            added_count=3,
            skipped_count=2,
            total_entries=100,
            movies_found=80,
            tv_shows_filtered=20,
            already_ranked=10,
        )

        assert session.user_id == "user-456"
        assert session.movies == movies
        assert session.created_at == created_at
        assert session.current_index == 5
        assert session.added_count == 3
        assert session.skipped_count == 2
        assert session.total_entries == 100
        assert session.movies_found == 80
        assert session.tv_shows_filtered == 20
        assert session.already_ranked == 10


class TestImportSessionStoreCreate:
    """Tests for ImportSessionStore.create_session method."""

    def test_create_session_returns_unique_id(self):
        """Test that create_session returns a unique session ID."""
        store = ImportSessionStore()
        movies = [{"title": "Movie 1"}]

        session_id_1 = store.create_session(
            user_id="user-1",
            movies=movies,
            total_entries=10,
            movies_found=8,
            tv_shows_filtered=2,
            already_ranked=1,
        )

        session_id_2 = store.create_session(
            user_id="user-2",
            movies=movies,
            total_entries=10,
            movies_found=8,
            tv_shows_filtered=2,
            already_ranked=1,
        )

        assert session_id_1 != session_id_2
        assert len(session_id_1) == 36  # UUID format
        assert len(session_id_2) == 36

    def test_create_session_stores_movies(self):
        """Test that created session contains provided movies."""
        store = ImportSessionStore()
        movies = [
            {"title": "The Matrix", "status": "pending"},
            {"title": "Inception", "status": "pending"},
        ]

        session_id = store.create_session(
            user_id="user-1",
            movies=movies,
            total_entries=5,
            movies_found=4,
            tv_shows_filtered=1,
            already_ranked=0,
        )

        session = store.get_session(session_id, "user-1")
        assert session is not None
        assert len(session.movies) == 2
        assert session.movies[0]["title"] == "The Matrix"
        assert session.movies[1]["title"] == "Inception"

    def test_create_session_stores_summary_stats(self):
        """Test that created session stores summary statistics."""
        store = ImportSessionStore()
        movies = []

        session_id = store.create_session(
            user_id="user-1",
            movies=movies,
            total_entries=100,
            movies_found=80,
            tv_shows_filtered=20,
            already_ranked=15,
        )

        session = store.get_session(session_id, "user-1")
        assert session is not None
        assert session.total_entries == 100
        assert session.movies_found == 80
        assert session.tv_shows_filtered == 20
        assert session.already_ranked == 15

    def test_create_session_replaces_existing_session(self):
        """Test that creating a new session replaces existing one for same user."""
        store = ImportSessionStore()
        movies_1 = [{"title": "First Movie"}]
        movies_2 = [{"title": "Second Movie"}]

        # Create first session
        session_id_1 = store.create_session(
            user_id="user-1",
            movies=movies_1,
            total_entries=1,
            movies_found=1,
            tv_shows_filtered=0,
            already_ranked=0,
        )

        # Create second session for same user
        session_id_2 = store.create_session(
            user_id="user-1",
            movies=movies_2,
            total_entries=2,
            movies_found=2,
            tv_shows_filtered=0,
            already_ranked=0,
        )

        # Session IDs should be different
        assert session_id_1 != session_id_2

        # Old session should be gone
        old_session = store.get_session(session_id_1, "user-1")
        assert old_session is None

        # New session should exist
        new_session = store.get_session(session_id_2, "user-1")
        assert new_session is not None
        assert new_session.movies[0]["title"] == "Second Movie"
        assert new_session.total_entries == 2

    def test_create_session_truncates_movies_at_500(self):
        """Test that movies list is truncated to MAX_MOVIES_PER_SESSION (500)."""
        store = ImportSessionStore()
        movies = [{"title": f"Movie {i}"} for i in range(600)]

        session_id = store.create_session(
            user_id="user-1",
            movies=movies,
            total_entries=600,
            movies_found=600,
            tv_shows_filtered=0,
            already_ranked=0,
        )

        session = store.get_session(session_id, "user-1")
        assert session is not None
        assert len(session.movies) == 500
        assert session.movies[0]["title"] == "Movie 0"
        assert session.movies[499]["title"] == "Movie 499"

    def test_create_session_sets_created_at(self):
        """Test that created session has a created_at timestamp."""
        store = ImportSessionStore()
        before = datetime.utcnow()

        session_id = store.create_session(
            user_id="user-1",
            movies=[],
            total_entries=0,
            movies_found=0,
            tv_shows_filtered=0,
            already_ranked=0,
        )

        after = datetime.utcnow()
        session = store.get_session(session_id, "user-1")
        assert session is not None
        assert before <= session.created_at <= after


class TestImportSessionStoreGet:
    """Tests for ImportSessionStore.get_session method."""

    def test_get_session_returns_session_for_owner(self):
        """Test that get_session returns session when user is owner."""
        store = ImportSessionStore()
        movies = [{"title": "Test Movie"}]

        session_id = store.create_session(
            user_id="user-1",
            movies=movies,
            total_entries=1,
            movies_found=1,
            tv_shows_filtered=0,
            already_ranked=0,
        )

        session = store.get_session(session_id, "user-1")
        assert session is not None
        assert session.user_id == "user-1"
        assert session.movies == movies

    def test_get_session_returns_none_for_non_owner(self):
        """Test that get_session returns None when user is not owner."""
        store = ImportSessionStore()
        movies = [{"title": "Test Movie"}]

        session_id = store.create_session(
            user_id="user-1",
            movies=movies,
            total_entries=1,
            movies_found=1,
            tv_shows_filtered=0,
            already_ranked=0,
        )

        # Try to access as different user
        session = store.get_session(session_id, "user-2")
        assert session is None

    def test_get_session_returns_none_for_nonexistent_id(self):
        """Test that get_session returns None for non-existent session ID."""
        store = ImportSessionStore()

        session = store.get_session("nonexistent-session-id", "user-1")
        assert session is None

    def test_get_session_returns_none_for_expired_session(self):
        """Test that get_session returns None for expired sessions."""
        store = ImportSessionStore()
        movies = [{"title": "Test Movie"}]

        session_id = store.create_session(
            user_id="user-1",
            movies=movies,
            total_entries=1,
            movies_found=1,
            tv_shows_filtered=0,
            already_ranked=0,
        )

        # Manually set created_at to 31 minutes ago (past TTL)
        session = store._sessions[session_id]
        session.created_at = datetime.utcnow() - timedelta(minutes=31)

        # Should return None due to expiry
        result = store.get_session(session_id, "user-1")
        assert result is None

        # Session should be deleted
        assert session_id not in store._sessions

    def test_get_session_deletes_expired_session(self):
        """Test that get_session deletes expired session from store."""
        store = ImportSessionStore()
        movies = [{"title": "Test Movie"}]

        session_id = store.create_session(
            user_id="user-1",
            movies=movies,
            total_entries=1,
            movies_found=1,
            tv_shows_filtered=0,
            already_ranked=0,
        )

        # Expire the session
        store._sessions[session_id].created_at = datetime.utcnow() - timedelta(minutes=31)

        # Access triggers deletion
        store.get_session(session_id, "user-1")

        # Verify session is deleted
        assert session_id not in store._sessions
        assert "user-1" not in store._user_sessions

    def test_get_session_returns_session_at_ttl_boundary(self):
        """Test that session is returned when exactly at TTL boundary."""
        store = ImportSessionStore()
        movies = [{"title": "Test Movie"}]

        session_id = store.create_session(
            user_id="user-1",
            movies=movies,
            total_entries=1,
            movies_found=1,
            tv_shows_filtered=0,
            already_ranked=0,
        )

        # Set to exactly 29 minutes ago (just under TTL)
        store._sessions[session_id].created_at = datetime.utcnow() - timedelta(minutes=29)

        # Should still return session
        result = store.get_session(session_id, "user-1")
        assert result is not None


class TestImportSessionStoreUpdate:
    """Tests for ImportSessionStore.update_session method."""

    def test_update_session_current_index(self):
        """Test updating current_index on a session."""
        store = ImportSessionStore()
        movies = [{"title": "Movie 1"}, {"title": "Movie 2"}]

        session_id = store.create_session(
            user_id="user-1",
            movies=movies,
            total_entries=2,
            movies_found=2,
            tv_shows_filtered=0,
            already_ranked=0,
        )

        updated = store.update_session(session_id, "user-1", current_index=1)
        assert updated is not None
        assert updated.current_index == 1

    def test_update_session_counts(self):
        """Test updating added_count and skipped_count."""
        store = ImportSessionStore()
        movies = []

        session_id = store.create_session(
            user_id="user-1",
            movies=movies,
            total_entries=0,
            movies_found=0,
            tv_shows_filtered=0,
            already_ranked=0,
        )

        updated = store.update_session(
            session_id, "user-1", added_count=5, skipped_count=3
        )
        assert updated is not None
        assert updated.added_count == 5
        assert updated.skipped_count == 3

    def test_update_session_movies_list(self):
        """Test updating movies list on a session."""
        store = ImportSessionStore()
        movies = [{"title": "Movie 1", "status": "pending"}]

        session_id = store.create_session(
            user_id="user-1",
            movies=movies,
            total_entries=1,
            movies_found=1,
            tv_shows_filtered=0,
            already_ranked=0,
        )

        updated_movies = [{"title": "Movie 1", "status": "added"}]
        updated = store.update_session(session_id, "user-1", movies=updated_movies)
        assert updated is not None
        assert updated.movies[0]["status"] == "added"

    def test_update_session_returns_none_for_non_owner(self):
        """Test that update_session returns None for non-owner."""
        store = ImportSessionStore()

        session_id = store.create_session(
            user_id="user-1",
            movies=[],
            total_entries=0,
            movies_found=0,
            tv_shows_filtered=0,
            already_ranked=0,
        )

        result = store.update_session(session_id, "user-2", current_index=5)
        assert result is None

    def test_update_session_returns_none_for_nonexistent(self):
        """Test that update_session returns None for non-existent session."""
        store = ImportSessionStore()

        result = store.update_session("nonexistent", "user-1", current_index=5)
        assert result is None

    def test_update_session_ignores_disallowed_fields(self):
        """Test that update_session ignores fields not in allowed list."""
        store = ImportSessionStore()

        session_id = store.create_session(
            user_id="user-1",
            movies=[],
            total_entries=10,
            movies_found=8,
            tv_shows_filtered=2,
            already_ranked=0,
        )

        original_created_at = store._sessions[session_id].created_at

        # Try to update disallowed fields (user_id is a positional arg so we
        # test total_entries and created_at which are keyword-only)
        updated = store.update_session(
            session_id,
            "user-1",
            total_entries=999,  # Should be ignored
        )

        assert updated is not None
        assert updated.user_id == "user-1"  # Unchanged
        assert updated.total_entries == 10  # Unchanged
        assert updated.created_at == original_created_at  # Unchanged


class TestImportSessionStoreDelete:
    """Tests for ImportSessionStore.delete_session method."""

    def test_delete_session_removes_session(self):
        """Test that delete_session removes the session from store."""
        store = ImportSessionStore()

        session_id = store.create_session(
            user_id="user-1",
            movies=[],
            total_entries=0,
            movies_found=0,
            tv_shows_filtered=0,
            already_ranked=0,
        )

        store.delete_session(session_id)

        assert session_id not in store._sessions
        assert "user-1" not in store._user_sessions

    def test_delete_session_removes_user_mapping(self):
        """Test that delete_session removes user-to-session mapping."""
        store = ImportSessionStore()

        session_id = store.create_session(
            user_id="user-1",
            movies=[],
            total_entries=0,
            movies_found=0,
            tv_shows_filtered=0,
            already_ranked=0,
        )

        assert "user-1" in store._user_sessions

        store.delete_session(session_id)

        assert "user-1" not in store._user_sessions

    def test_delete_nonexistent_session_is_safe(self):
        """Test that deleting non-existent session doesn't raise error."""
        store = ImportSessionStore()

        # Should not raise
        store.delete_session("nonexistent-session-id")


class TestImportSessionStoreCleanup:
    """Tests for ImportSessionStore.cleanup_expired method."""

    def test_cleanup_removes_expired_sessions(self):
        """Test that cleanup_expired removes all expired sessions."""
        store = ImportSessionStore()

        # Create several sessions
        session_id_1 = store.create_session(
            user_id="user-1",
            movies=[],
            total_entries=0,
            movies_found=0,
            tv_shows_filtered=0,
            already_ranked=0,
        )
        session_id_2 = store.create_session(
            user_id="user-2",
            movies=[],
            total_entries=0,
            movies_found=0,
            tv_shows_filtered=0,
            already_ranked=0,
        )
        session_id_3 = store.create_session(
            user_id="user-3",
            movies=[],
            total_entries=0,
            movies_found=0,
            tv_shows_filtered=0,
            already_ranked=0,
        )

        # Expire sessions 1 and 2
        store._sessions[session_id_1].created_at = datetime.utcnow() - timedelta(minutes=31)
        store._sessions[session_id_2].created_at = datetime.utcnow() - timedelta(minutes=60)
        # Session 3 remains fresh

        count = store.cleanup_expired()

        assert count == 2
        assert session_id_1 not in store._sessions
        assert session_id_2 not in store._sessions
        assert session_id_3 in store._sessions

    def test_cleanup_returns_count_of_removed_sessions(self):
        """Test that cleanup_expired returns correct count."""
        store = ImportSessionStore()

        # Create sessions
        for i in range(5):
            session_id = store.create_session(
                user_id=f"user-{i}",
                movies=[],
                total_entries=0,
                movies_found=0,
                tv_shows_filtered=0,
                already_ranked=0,
            )
            # Expire all sessions
            store._sessions[session_id].created_at = datetime.utcnow() - timedelta(minutes=31)

        count = store.cleanup_expired()
        assert count == 5

    def test_cleanup_returns_zero_when_no_expired(self):
        """Test that cleanup_expired returns 0 when no expired sessions."""
        store = ImportSessionStore()

        # Create fresh sessions
        store.create_session(
            user_id="user-1",
            movies=[],
            total_entries=0,
            movies_found=0,
            tv_shows_filtered=0,
            already_ranked=0,
        )

        count = store.cleanup_expired()
        assert count == 0


class TestImportSessionStoreSessionCount:
    """Tests for ImportSessionStore.get_session_count method."""

    def test_get_session_count_empty_store(self):
        """Test that get_session_count returns 0 for empty store."""
        store = ImportSessionStore()
        assert store.get_session_count() == 0

    def test_get_session_count_with_sessions(self):
        """Test that get_session_count returns correct count."""
        store = ImportSessionStore()

        for i in range(3):
            store.create_session(
                user_id=f"user-{i}",
                movies=[],
                total_entries=0,
                movies_found=0,
                tv_shows_filtered=0,
                already_ranked=0,
            )

        assert store.get_session_count() == 3


class TestGlobalSessionStore:
    """Tests for the global import_session_store instance."""

    def test_global_store_exists(self):
        """Test that global store instance exists."""
        assert import_session_store is not None
        assert isinstance(import_session_store, ImportSessionStore)

    def test_global_store_has_correct_constants(self):
        """Test that global store has correct TTL and limit constants."""
        assert import_session_store.SESSION_TTL_MINUTES == 30
        assert import_session_store.MAX_MOVIES_PER_SESSION == 500
