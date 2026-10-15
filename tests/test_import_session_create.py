"""Tests for ImportSession, store creation, session count and the global store."""

from app.utils.time import utc_now_naive
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
            created_at=utc_now_naive(),
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
        created_at = utc_now_naive()
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
        before = utc_now_naive()

        session_id = store.create_session(
            user_id="user-1",
            movies=[],
            total_entries=0,
            movies_found=0,
            tv_shows_filtered=0,
            already_ranked=0,
        )

        after = utc_now_naive()
        session = store.get_session(session_id, "user-1")
        assert session is not None
        assert before <= session.created_at <= after


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
