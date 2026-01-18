# Task 01: Backend Schemas and Session Storage

**Feature:** amazon-prime-import
**Agent:** backend-implementation
**Status:** Not Started
**Blocked By:** None

---

## Objective

Create the Pydantic schemas for import API requests/responses and implement the in-memory session storage service for managing import sessions.

---

## Context

The Amazon Prime import feature requires temporary session storage to hold parsed/matched movies during the multi-step review workflow. Sessions are user-specific, expire after 30 minutes, and are stored in-memory (acceptable for single-server deployment).

### Relevant FRD Sections
- FRD Section: "Session Storage" - 30 minute TTL, 500 movie limit
- FRD Section: "API Design" - Response schemas for session endpoints

### Relevant Refinement Notes
- Use in-memory dict with TTL, similar to OAuth state pattern
- Sessions lost on server restart is acceptable for MVP
- Replace existing session if user starts new import

---

## Scope

### In Scope
- Create `app/schemas/import_amazon.py` with all import-related schemas
- Create `app/services/import_session.py` with session store class
- Export schemas from `app/schemas/__init__.py`

### Out of Scope
- CSV parsing logic (task-02)
- API endpoints (task-03)
- TMDB matching logic (handled in task-03 with existing TMDBService)

---

## Implementation Notes

### Key Files

| File | Action | Notes |
|------|--------|-------|
| `/Users/stephen/Projects/movie-ranking/app/schemas/import_amazon.py` | Create | All import schemas |
| `/Users/stephen/Projects/movie-ranking/app/services/import_session.py` | Create | Session store class |
| `/Users/stephen/Projects/movie-ranking/app/schemas/__init__.py` | Modify | Export new schemas |

### Patterns to Follow

- Schema pattern: See `/Users/stephen/Projects/movie-ranking/app/schemas/ranking.py`
- Session storage pattern: Similar to OAuth state in `/Users/stephen/Projects/movie-ranking/app/routers/google_auth.py`

### Schema Definitions

```python
# app/schemas/import_amazon.py

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ParsedMovieItem(BaseModel):
    """A movie parsed from the CSV file."""
    title: str
    watch_date: datetime | None
    prime_image_url: str | None


class TMDBMatchResult(BaseModel):
    """TMDB search result for matching."""
    model_config = ConfigDict(from_attributes=True)

    tmdb_id: int
    title: str
    year: int | None
    poster_url: str | None
    overview: str | None


class MatchedMovieItem(BaseModel):
    """A parsed movie with TMDB match results."""
    parsed: ParsedMovieItem
    tmdb_match: TMDBMatchResult | None
    confidence: float = Field(ge=0.0, le=1.0)
    alternatives: list[TMDBMatchResult] = []
    status: Literal["pending", "added", "skipped"] = "pending"


class ImportSessionResponse(BaseModel):
    """Response after uploading CSV file."""
    session_id: str
    total_entries: int
    movies_found: int
    tv_shows_filtered: int
    already_ranked: int
    ready_for_review: int
    movies: list[MatchedMovieItem]


class ImportSessionDetailResponse(BaseModel):
    """Current session state."""
    session_id: str
    current_index: int
    total_movies: int
    added_count: int
    skipped_count: int
    remaining_count: int
    movies: list[MatchedMovieItem]


class ImportMovieAddRequest(BaseModel):
    """Request to add a movie from import session."""
    rating: int = Field(ge=1, le=5)
    rated_at: datetime | None = None  # Defaults to watch_date from CSV


class ImportCompletionResponse(BaseModel):
    """Summary after completing import."""
    movies_added: int
    movies_skipped: int
    unmatched_titles: list[str]
```

### Session Store Implementation

```python
# app/services/import_session.py

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional
from uuid import uuid4


@dataclass
class ImportSession:
    """Represents an active import session."""
    user_id: str
    movies: list  # List of MatchedMovieItem dicts
    created_at: datetime
    current_index: int = 0
    added_count: int = 0
    skipped_count: int = 0
    # Summary stats from upload
    total_entries: int = 0
    movies_found: int = 0
    tv_shows_filtered: int = 0
    already_ranked: int = 0


class ImportSessionStore:
    """In-memory store for import sessions with automatic cleanup."""

    SESSION_TTL_MINUTES = 30
    MAX_MOVIES_PER_SESSION = 500

    def __init__(self):
        self._sessions: Dict[str, ImportSession] = {}
        self._user_sessions: Dict[str, str] = {}  # user_id -> session_id mapping

    def create_session(
        self,
        user_id: str,
        movies: list,
        total_entries: int,
        movies_found: int,
        tv_shows_filtered: int,
        already_ranked: int,
    ) -> str:
        """Create a new import session, replacing any existing session for this user."""
        # Remove existing session for this user
        if user_id in self._user_sessions:
            old_session_id = self._user_sessions[user_id]
            self._sessions.pop(old_session_id, None)

        session_id = str(uuid4())
        self._sessions[session_id] = ImportSession(
            user_id=user_id,
            movies=movies[:self.MAX_MOVIES_PER_SESSION],
            created_at=datetime.utcnow(),
            total_entries=total_entries,
            movies_found=movies_found,
            tv_shows_filtered=tv_shows_filtered,
            already_ranked=already_ranked,
        )
        self._user_sessions[user_id] = session_id
        return session_id

    def get_session(self, session_id: str, user_id: str) -> Optional[ImportSession]:
        """Get a session if it exists, belongs to the user, and hasn't expired."""
        session = self._sessions.get(session_id)
        if session is None:
            return None

        # Check ownership
        if session.user_id != user_id:
            return None

        # Check expiry
        if datetime.utcnow() - session.created_at > timedelta(minutes=self.SESSION_TTL_MINUTES):
            self.delete_session(session_id)
            return None

        return session

    def delete_session(self, session_id: str) -> None:
        """Delete a session."""
        session = self._sessions.pop(session_id, None)
        if session:
            self._user_sessions.pop(session.user_id, None)

    def cleanup_expired(self) -> int:
        """Remove all expired sessions. Returns count of removed sessions."""
        now = datetime.utcnow()
        expired = [
            sid for sid, session in self._sessions.items()
            if now - session.created_at > timedelta(minutes=self.SESSION_TTL_MINUTES)
        ]
        for sid in expired:
            self.delete_session(sid)
        return len(expired)


# Global session store instance
import_session_store = ImportSessionStore()
```

### Technical Decisions

- **Global store instance:** Single instance for simple access from router, similar to settings pattern
- **User session mapping:** Track one session per user to enable replacement on new upload
- **No async needed:** Dict operations are fast enough; no async context manager required

---

## Acceptance Criteria

- [ ] `ParsedMovieItem` schema correctly represents CSV-parsed movie data
- [ ] `MatchedMovieItem` schema includes TMDB match, confidence score, and alternatives
- [ ] `ImportSessionResponse` schema matches FRD specification
- [ ] `ImportSessionDetailResponse` schema includes progress tracking fields
- [ ] `ImportMovieAddRequest` schema validates rating (1-5) and optional rated_at
- [ ] `ImportSessionStore` creates sessions with unique IDs
- [ ] `ImportSessionStore` enforces user ownership on session access
- [ ] `ImportSessionStore` expires sessions after 30 minutes
- [ ] `ImportSessionStore` replaces existing session when user starts new import
- [ ] `ImportSessionStore` limits movies to 500 per session
- [ ] Schemas exported from `app/schemas/__init__.py`

---

## Testing Requirements

- [ ] Unit tests for ImportSessionStore.create_session()
- [ ] Unit tests for ImportSessionStore.get_session() with valid/invalid user
- [ ] Unit tests for session expiry logic
- [ ] Unit tests for session replacement on new upload
- [ ] Unit tests for 500 movie limit truncation

---

## Handoff Notes

### For Next Task (task-02)
- Use `ParsedMovieItem` schema for CSV parser output
- Session store is ready for use via `import_session_store` global instance

### Artifacts Produced
- `/Users/stephen/Projects/movie-ranking/app/schemas/import_amazon.py`
- `/Users/stephen/Projects/movie-ranking/app/services/import_session.py`
