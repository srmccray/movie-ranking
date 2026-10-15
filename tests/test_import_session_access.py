"""Tests for ImportSessionStore get, update, delete and cleanup."""

from datetime import datetime, timedelta

from app.services.import_session import (
    ImportSessionStore,
)


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


