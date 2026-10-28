# Backend Development Guide

This document provides FastAPI/Python development guidance for the Movie Ranking API backend.

> **Important:** Before reading this guide, review the [root CLAUDE.md](../CLAUDE.md) for project-wide conventions including trailing slashes, datetime handling, HTTP status codes, and API contract verification. This guide focuses on backend-specific patterns and implementation details.

## Project Structure

```
app/
  __init__.py
  main.py              # FastAPI app, lifespan (DB check), CORS, router registration, /health
  config.py            # Settings via pydantic-settings (DB, JWT, TMDB, Google OAuth)
  database.py          # Async engine (SQLite/Lambda/Postgres pooling), Base, get_db, DbSession
  dependencies.py      # Auth dependencies (CurrentUser, get_current_user)
  models/
    __init__.py        # Re-exports all models
    user.py            # User (local and/or Google auth)
    movie.py           # Movie (TMDB metadata fields)
    ranking.py         # Ranking (user_id + movie_id unique, rating 1-5, rated_at)
    oauth_state.py     # OAuthState (short-lived CSRF state for Google OAuth)
  schemas/
    __init__.py        # Re-exports most schemas (analytics schemas are imported from app.schemas.analytics)
    user.py            # UserCreate, UserResponse, UserProfileResponse
    movie.py           # MovieCreate, MovieResponse, MovieBrief, TMDBSearchResult, TMDBSearchResponse, ...
    ranking.py         # RankingCreate, RankingResponse, RankingWithMovie, RankingListResponse
    token.py           # Token
    oauth.py           # GoogleAuthUrlResponse, GoogleCallbackError, AccountLinkingResponse
    analytics.py       # ActivityResponse, GenreResponse, StatsResponse, RatingDistributionResponse
    import_amazon.py   # Amazon Prime import request/response schemas
  routers/
    __init__.py
    auth.py            # /register, /login, /me/ (mounted at /api/v1/auth)
    google_auth/       # package: oauth.py (state + Google token helpers), login.py, link.py; routes /google/login/, /google/callback/, /google/link/, /google/link/callback/ (also /api/v1/auth)
    movies.py          # GET /search/ (TMDB search), POST / (get-or-create movie) -- no list/get/update/delete
    rankings.py        # Ranking upsert, paginated list, delete one, delete all
    analytics.py       # /activity/, /genres/, /stats/, /rating-distribution/
    import_amazon/     # package: matching.py, session.py, review.py; /amazon-prime/... CSV import (mounted at /api/v1/import)
  services/
    __init__.py
    movies.py          # find_movie_by_tmdb_id, create_movie, backfill_missing_metadata (shared by movies and import routers)
    tmdb.py            # TMDBService (async httpx client), search_movies, get_movie_details
    csv_parser.py      # parse_amazon_prime_csv
    import_session.py  # In-memory ImportSessionStore (import_session_store singleton)
  utils/
    __init__.py
    security.py        # Password hashing, JWT encode/decode
alembic/
  env.py               # Async migration config (reads DATABASE_URL from settings)
  versions/
    001_initial_schema.py ... 008_datetime_columns_to_naive_utc.py  (see Creating Migrations)
tests/                 # At the repo root, not inside app/
  __init__.py
  conftest.py          # Fixtures: client, test_user, auth_headers, test_movie
  test_auth.py, test_google_auth.py, test_movies.py, test_rankings.py, test_analytics.py,
  test_import_amazon.py, test_import_session.py, test_csv_parser.py, test_tmdb_service.py
```

## Adding a New Model

### Step 1: Create the Model File

Create `app/models/<entity>.py`:

```python
"""<Entity> model for <description>."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User  # Avoid circular imports


class Entity(Base):
    """Entity model representing <description>.

    Attributes:
        id: Unique identifier (UUID).
        user_id: Foreign key to users table.
        name: Entity name.
        created_at: Record creation timestamp.
        updated_at: Last update timestamp.
        user: Associated User (relationship).
    """

    __tablename__ = "entities"

    # Primary key - always use UUID with server-side generation
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    # Foreign keys - use CASCADE for cleanup
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Regular fields with appropriate types
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    value: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Timestamps - always include both
    created_at: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=utc_now_naive,  # from app.utils.time
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="entities",  # Add to User model too
        lazy="joined",  # or "selectin" for collections
    )

    __table_args__ = (
        # Constraints
        CheckConstraint(
            "value IS NULL OR (value >= 0 AND value <= 100)",
            name="chk_value_range",
        ),
        # Indexes for query optimization
        Index("idx_entities_user_id", "user_id"),
        Index("idx_entities_name", "name"),
    )

    def __repr__(self) -> str:
        """Return string representation of Entity."""
        return f"<Entity(id={self.id}, name={self.name})>"
```

### Step 2: Export from `app/models/__init__.py`

```python
"""SQLAlchemy models for the Movie Ranking API."""

from app.models.entity import Entity  # Add this
from app.models.movie import Movie
from app.models.oauth_state import OAuthState
from app.models.ranking import Ranking
from app.models.user import User

__all__ = ["Entity", "Movie", "OAuthState", "Ranking", "User"]  # Add to list
```

### Step 3: Add Relationship to Related Models

If your model relates to User, add in `app/models/user.py`:

```python
if TYPE_CHECKING:
    from app.models.entity import Entity  # Add import

# In the class, add relationship
entities: Mapped[list["Entity"]] = relationship(
    "Entity",
    back_populates="user",
    cascade="all, delete-orphan",
    lazy="selectin",
)
```

### Model Conventions

| Pattern | Example |
|---------|---------|
| Primary key | `id: Mapped[UUID]` with `server_default=text("gen_random_uuid()")` |
| Foreign key | `user_id: Mapped[UUID]` with `ForeignKey("users.id", ondelete="CASCADE")` |
| String fields | `String(length)` - use 255 for names, 500 for titles, longer for content |
| Timestamps | Always include `created_at` and `updated_at` with server defaults |
| Nullable fields | Use `Mapped[int | None]` for optional fields |
| Relationships | Use `lazy="joined"` for single objects, `lazy="selectin"` for collections |
| Constraints | Use CheckConstraint for validation, UniqueConstraint for uniqueness |
| Indexes | Add for foreign keys and frequently queried columns |

---

## Adding New Schemas

### Step 1: Create the Schema File

Create `app/schemas/<entity>.py`:

```python
"""Entity schemas for request/response validation."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EntityCreate(BaseModel):
    """Schema for creating a new entity.

    Attributes:
        name: Entity name (1-255 characters).
        value: Optional value (0-100).
    """

    name: str = Field(..., min_length=1, max_length=255)
    value: Optional[int] = Field(None, ge=0, le=100)


class EntityUpdate(BaseModel):
    """Schema for updating an entity (all fields optional).

    Attributes:
        name: New entity name.
        value: New value.
    """

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    value: Optional[int] = Field(None, ge=0, le=100)


class EntityResponse(BaseModel):
    """Schema for entity response with full details.

    Attributes:
        id: Unique entity identifier.
        name: Entity name.
        value: Entity value (optional).
        created_at: Record creation timestamp.
        updated_at: Last update timestamp.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    value: Optional[int]
    created_at: datetime
    updated_at: datetime


class EntityBrief(BaseModel):
    """Abbreviated entity schema for embedding in other responses.

    Attributes:
        id: Unique entity identifier.
        name: Entity name.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class EntityListResponse(BaseModel):
    """Schema for paginated entity list response.

    Attributes:
        items: List of entities.
        total: Total number of entities.
        limit: Number of results requested.
        offset: Number of results skipped.
    """

    items: List[EntityResponse]
    total: int
    limit: int
    offset: int
```

### Step 2: Export from `app/schemas/__init__.py`

```python
"""Pydantic schemas for request/response validation."""

from app.schemas.entity import (
    EntityBrief,
    EntityCreate,
    EntityListResponse,
    EntityResponse,
    EntityUpdate,
)
# ... other imports

__all__ = [
    "EntityBrief",
    "EntityCreate",
    "EntityListResponse",
    "EntityResponse",
    "EntityUpdate",
    # ... others
]
```

### Schema Conventions

| Pattern | Usage |
|---------|-------|
| `ConfigDict(from_attributes=True)` | Required on all response schemas to convert SQLAlchemy models |
| `Field(..., min_length=1)` | Required fields with validation |
| `Field(None, ge=0)` | Optional fields with constraints |
| `Optional[type]` | Always use for nullable fields |
| Nested schemas | Create `*Brief` schemas for embedding (e.g., `MovieBrief`) |
| Paginated lists | Include `items`, `total`, `limit`, `offset` (see `RankingListResponse`) |
| Other wrappers | Analytics and import endpoints use named wrappers (`activity`, `genres`, `distribution`, `movies`); see their schemas |

---

## Frontend API Contract Documentation

> **Note:** See the [root CLAUDE.md](../CLAUDE.md) for the complete API contract verification requirements. This section covers backend-specific documentation patterns.

### Exporting the OpenAPI Schema

```bash
venv/bin/python scripts/export_openapi.py [--out frontend/openapi.json]
```

Runs offline (dummy env, no database). Output is deterministic (sorted keys, trailing newline). `tests/test_api_conventions.py` fails if an `/api/v1` path lacks a trailing slash (only `/auth/register` and `/auth/login` are excepted) or an operation has no declared success response.

### Schema Documentation Requirements

**All response schemas MUST include clear docstrings that explicitly state the response structure:**

```python
class TMDBSearchResponse(BaseModel):
    """Schema for TMDB search response.

    RESPONSE SHAPE: { results: [...], query: "...", year: ... }

    This is a wrapper response - the actual search results are in the 'results' field,
    not returned as a top-level array.

    Attributes:
        results: List of movies matching the search query.
        query: The original search query (echoed back).
        year: The year filter used (if any).
    """

    results: list[TMDBSearchResult] = Field(..., description="List of matching movies")
    query: str = Field(..., description="The search query")
    year: Optional[int] = Field(None, description="Year filter used")
```

### Wrapper vs Direct Response Patterns

**Document which pattern each endpoint uses:**

| Pattern | When to Use | Example |
|---------|-------------|---------|
| Direct response | Single item create/update | `MovieResponse` for POST /movies/, `RankingResponse` for POST /rankings/ |
| List wrapper | Paginated collections | `RankingListResponse` (`items`, `total`, `limit`, `offset`) for GET /rankings/ |
| Search wrapper | Search results with metadata | `TMDBSearchResponse` (`results`, `query`, `year`) for GET /movies/search/ |
| Analytics wrapper | Aggregates for charts | `ActivityResponse` (`activity`, `start_date`, `end_date`), `GenreResponse` (`genres`, `total_movies`), `RatingDistributionResponse` (`distribution`, `total`); `StatsResponse` is a flat object |
| Import wrapper | Amazon import session | `ImportSessionResponse` / `ImportSessionDetailResponse` (`movies` list plus counters) |
| No body | Deletes and skip | 204 for `DELETE /rankings/{id}/`, `DELETE /rankings/all/`, import skip and cancel |

### Router Documentation

**Always document the response shape in router docstrings:**

```python
@router.get(
    "/search/",
    response_model=TMDBSearchResponse,  # <-- Explicit response model
    summary="Search movies on TMDB",
)
async def search_tmdb_movies(...) -> TMDBSearchResponse:
    """Search for movies on TMDB.

    Returns:
        TMDBSearchResponse: Wrapper containing:
            - results: List of TMDBSearchResult objects
            - query: The search query (echoed)
            - year: Year filter if provided

        NOTE: Results are wrapped in a response object, not returned as a raw list.
    """
```

### Field Naming Convention

**Always use snake_case for all schema fields.** Frontend will use these names directly:

```python
# CORRECT - snake_case matches JSON output
class TMDBSearchResult(BaseModel):
    tmdb_id: int
    poster_url: Optional[str]

# WRONG - camelCase causes frontend mismatch
class TMDBSearchResult(BaseModel):
    tmdbId: int  # Frontend would need { tmdb_id: ... } but gets { tmdbId: ... }
    posterUrl: Optional[str]
```

### Testing Response Shapes

**Integration tests should verify the exact response structure:**

```python
@pytest.mark.asyncio
async def test_search_returns_wrapped_response(self, client, auth_headers):
    """Verify search endpoint returns wrapper object, not raw array."""
    response = await client.get(
        "/api/v1/movies/search/",
        params={"q": "test"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Verify wrapper structure
    assert "results" in data, "Response must wrap results in 'results' field"
    assert "query" in data, "Response must include echoed query"
    assert isinstance(data["results"], list), "results must be a list"
```

---

## Adding a New Router

### Step 1: Create the Router File

Create `app/routers/<entities>.py`:

```python
"""Entities router for CRUD operations on entities."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.database import DbSession
from app.dependencies import CurrentUser
from app.models.entity import Entity
from app.schemas.entity import (
    EntityCreate,
    EntityListResponse,
    EntityResponse,
    EntityUpdate,
)

router = APIRouter(tags=["entities"])


@router.post(
    "/",  # NOTE: Trailing slash required (see root CLAUDE.md)
    response_model=EntityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new entity",
    responses={
        201: {"description": "Entity created successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
async def create_entity(
    entity_data: EntityCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> Entity:
    """Create a new entity.

    Args:
        entity_data: Entity data containing name and optional value.
        current_user: The authenticated user (from JWT token).
        db: Async database session.

    Returns:
        The created entity with id and timestamps.

    Raises:
        HTTPException: 401 Unauthorized if not authenticated.
    """
    new_entity = Entity(
        user_id=current_user.id,
        name=entity_data.name,
        value=entity_data.value,
    )

    db.add(new_entity)
    await db.flush()
    await db.refresh(new_entity)

    return new_entity


@router.get(
    "/",  # NOTE: Trailing slash required
    response_model=EntityListResponse,
    summary="List user's entities",
    responses={
        200: {"description": "Entities retrieved successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def list_entities(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> EntityListResponse:
    """List all entities for the authenticated user.

    Args:
        current_user: The authenticated user (from JWT token).
        db: Async database session.
        limit: Number of results to return (1-100, default 20).
        offset: Number of results to skip (default 0).

    Returns:
        Paginated list of entities.
    """
    # Get total count
    count_result = await db.execute(
        select(func.count()).where(Entity.user_id == current_user.id)
    )
    total = count_result.scalar_one()

    # Get paginated results
    result = await db.execute(
        select(Entity)
        .where(Entity.user_id == current_user.id)
        .order_by(Entity.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    entities = result.scalars().all()

    return EntityListResponse(
        items=list(entities),
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{entity_id}/",  # NOTE: Trailing slash required
    response_model=EntityResponse,
    summary="Get entity by ID",
    responses={
        200: {"description": "Entity retrieved successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this entity"},
        404: {"description": "Entity not found"},
    },
)
async def get_entity(
    entity_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> Entity:
    """Get a single entity by ID.

    Args:
        entity_id: UUID of the entity to retrieve.
        current_user: The authenticated user (from JWT token).
        db: Async database session.

    Returns:
        The requested entity.

    Raises:
        HTTPException: 404 if not found, 403 if not owner.
    """
    result = await db.execute(select(Entity).where(Entity.id == entity_id))
    entity = result.scalar_one_or_none()

    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity not found",
        )

    if entity.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this entity",
        )

    return entity


@router.put(
    "/{entity_id}/",  # NOTE: Trailing slash required
    response_model=EntityResponse,
    summary="Update an entity",
    responses={
        200: {"description": "Entity updated successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to update this entity"},
        404: {"description": "Entity not found"},
    },
)
async def update_entity(
    entity_id: UUID,
    entity_data: EntityUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> Entity:
    """Update an entity by ID.

    Args:
        entity_id: UUID of the entity to update.
        entity_data: Fields to update.
        current_user: The authenticated user (from JWT token).
        db: Async database session.

    Returns:
        The updated entity.
    """
    result = await db.execute(select(Entity).where(Entity.id == entity_id))
    entity = result.scalar_one_or_none()

    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity not found",
        )

    if entity.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this entity",
        )

    # Update only provided fields
    if entity_data.name is not None:
        entity.name = entity_data.name
    if entity_data.value is not None:
        entity.value = entity_data.value

    await db.flush()
    await db.refresh(entity)

    return entity


@router.delete(
    "/{entity_id}/",  # NOTE: Trailing slash required
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an entity",
    responses={
        204: {"description": "Entity deleted successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to delete this entity"},
        404: {"description": "Entity not found"},
    },
)
async def delete_entity(
    entity_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """Delete an entity by ID.

    Args:
        entity_id: UUID of the entity to delete.
        current_user: The authenticated user (from JWT token).
        db: Async database session.

    Raises:
        HTTPException: 404 if not found, 403 if not owner.
    """
    result = await db.execute(select(Entity).where(Entity.id == entity_id))
    entity = result.scalar_one_or_none()

    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity not found",
        )

    if entity.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this entity",
        )

    await db.delete(entity)
    await db.flush()
```

### Step 2: Register in `app/main.py`

```python
from app.routers import auth, entities, movies, rankings  # Add entities

# In router registration section:
app.include_router(entities.router, prefix="/api/v1/entities")
```

### Router Conventions

| Convention | Pattern |
|------------|---------|
| Tags | Use `tags=["entities"]` matching resource name |
| Response model | Always specify `response_model=` |
| Responses dict | Document all possible response codes |
| Dependencies | Use `CurrentUser` for auth, `DbSession` for database |
| Query params | Use `Query(default=X, ge=Y, le=Z)` for pagination |
| Path params | Use `{id}/` pattern with trailing slash |
| Authorization | Always check `entity.user_id != current_user.id` for ownership |

> **Important:** All endpoint paths MUST end with `/`. See the [root CLAUDE.md](../CLAUDE.md) for details on the trailing slash convention.
>
> **Known exceptions:** `POST /api/v1/auth/register` and `POST /api/v1/auth/login` are declared without a trailing slash (`/me/` and the Google routes have one). Do not copy this for new endpoints.

---

## Existing API Surface

All routes are mounted in `app/main.py` under `/api/v1/...` (plus `GET /health` and `GET /` at the root). All routes below require a Bearer token (`CurrentUser`) unless noted.

| Prefix | Endpoint | Response |
|--------|----------|----------|
| `/auth` | `POST /register` (no auth, 201, 409 on duplicate email) | `Token` |
| `/auth` | `POST /login` (no auth, form data, 401 on bad credentials) | `Token` |
| `/auth` | `GET /me/` | `UserProfileResponse` (`auth_provider`, `has_google_linked`, `has_password`) |
| `/auth` | `GET /google/login/`, `GET /google/link/` | `GoogleAuthUrlResponse` (`/google/link/` needs auth; 409 if already linked) |
| `/auth` | `GET /google/callback/`, `GET /google/link/callback/` | See "Google OAuth" below |
| `/movies` | `GET /search/?q=&year=` | `TMDBSearchResponse` (503 on TMDB rate limit, 500 on other TMDB errors) |
| `/movies` | `POST /` | `MovieResponse`; get-or-create by `tmdb_id`: 201 on create, 200 when a movie with that `tmdb_id` already exists (NULL metadata back-filled); a null `tmdb_id` always creates. Logic lives in `services/movies.py`, shared with the Amazon import |
| `/rankings` | `POST /` | `RankingResponse`; 201 on create, 200 when updating an existing ranking; 404 if movie missing |
| `/rankings` | `GET /?limit=&offset=&sort_by=&sort_order=` | `RankingListResponse`; `sort_by` is `rated_at` (default), `rating`, `title` or `year`; `sort_order` `desc` (default) or `asc`; limit 1-100 (default 20) |
| `/rankings` | `DELETE /{ranking_id}/` (204; 404/403) | none |
| `/rankings` | `DELETE /all/` (204, deletes all of the user's rankings) | none |
| `/analytics` | `GET /activity/`, `/genres/`, `/stats/`, `/rating-distribution/` | `ActivityResponse`, `GenreResponse`, `StatsResponse`, `RatingDistributionResponse` |
| `/import` | `POST /amazon-prime/upload/` and session routes | See "Amazon Prime Import" below |

### Google OAuth (`routers/google_auth/`)

- Requires `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` (default empty); login/link return 500 "Google OAuth not configured" when unset. `GOOGLE_REDIRECT_URI` defaults to `http://localhost:8000/api/v1/auth/google/callback/`.
- `GET /google/login/` creates an `OAuthState` row (random `state`, optional `redirect_uri` query param, `flow_type="login"`, 5-minute expiry) and returns the Google authorization URL. Expired states are cleaned up when new ones are created.
- `GET /google/callback/` validates and deletes the state, exchanges the code, verifies the Google ID token (email must be present and verified), then: finds the user by `google_id`; else by email and links it (`auth_provider="linked"`); else creates a user with `hashed_password=None` and `auth_provider="google"`. It sets the `session` (httpOnly) and `csrf_token` cookies on the response, then returns `Token` JSON, or a 302 to the stored `redirect_uri` if one exists. The redirect `Location` is always the stored URL with no token appended (the legacy `?token=` branch and `GOOGLE_LEGACY_TOKEN_IN_URL` setting were removed by TASK-0047). A link-flow state is bound to the browser: the `session` cookie must belong to the user who started the link, otherwise the callback redirects with `?error=session_mismatch` and links nothing (applies to `/google/link/callback/` too). Errors return 400 (cancelled, missing params, invalid/expired state, unverified email).
- Account linking: `GET /google/link/` (authenticated) stores the user id with `flow_type="link"`. The shared `/google/callback/` routes link-flow states to the link handler, and `/google/link/callback/` also exists; both respond with 302 redirects (errors go to `/settings?error=...`) rather than JSON.
- Users created via Google have no password, so `/login` returns 401 for them (`hashed_password is None`).

### Analytics (`routers/analytics.py`)

All four endpoints are `GET`, take no query parameters, and are scoped to the current user. `activity` and `genres` cover a rolling window (activity runs from the Sunday on or before the first of the month one year ago through the end of the current month, and omits zero-activity days). `rating-distribution` always returns all five ratings 1-5. Genre names come from the static `GENRE_MAP` (TMDB id to name) in `app/constants/genres.py` (`genre_name()` supplies the `Unknown (<id>)` fallback; shared query and counting helpers live in `app/services/analytics_genres.py`), using `Movie.genre_ids`. Watch time uses `Movie.runtime`.

### TMDB (`services/tmdb.py`)

`TMDBService` is an async context manager over `httpx` (10s timeout) configured by `TMDB_API_KEY` (required), `TMDB_BASE_URL`, `TMDB_IMAGE_BASE_URL`. Use `async with TMDBService() as service: await service.search_movies(query, year)`; module-level `search_movies` and `get_movie_details` helpers also exist. Errors: `TMDBServiceError` (base), `TMDBRateLimitError`, `TMDBAPIError`; routers map them to HTTP 503/500. Tests must mock TMDB rather than call it.

### Amazon Prime Import (`routers/import_amazon/`)

Multi-step workflow mounted at `/api/v1/import`; all routes require auth:

| Endpoint | Behavior |
|----------|----------|
| `POST /amazon-prime/upload/` (multipart `file`) | 201 `ImportSessionResponse`. 400 if not `.csv`, empty/unparseable, or no movies. Parses via `services/csv_parser.py` (UTF-8 then Latin-1; only `Type == Movie` rows kept, TV filtered), matches each movie against TMDB (best result plus up to 2 `alternatives`; `confidence` = 60% title similarity + 40% year match; pauses 1s every 35 searches; rate-limited or failed lookups become unmatched items with `tmdb_match=None`), skips movies the user already ranked (counted in `already_ranked`), and stores the result in a session |
| `GET /amazon-prime/session/{session_id}/` | `ImportSessionDetailResponse`; 404 if missing, expired or owned by another user |
| `POST /amazon-prime/session/{session_id}/movie/{index}/add/` | Body `ImportMovieAddRequest` (`rating` 1-5, optional `rated_at`; falls back to CSV watch date, then now). Creates or enriches the `Movie` by `tmdb_id` (fetching runtime), upserts the `Ranking`, marks the item `added`. 201 `RankingResponse`; 404 bad session/index; 400 if already processed or no TMDB match |
| `POST .../movie/{index}/skip/` | 204; marks `skipped`; 400 if already processed |
| `PATCH .../movie/{index}/match/` | Body `ImportMovieMatchRequest` (TMDB fields); sets that match with `confidence=1.0` and clears alternatives; returns `MatchedMovieItem` |
| `DELETE /amazon-prime/session/{session_id}/` | 204; deletes the session |

`index` is the 0-based position in the session's `movies` list. Sessions live in the in-memory `import_session_store` (`services/import_session.py`): one session per user (a new upload replaces the old one), 30-minute TTL, max 500 movies, lost on server restart (and not shared between Lambda instances or workers). Session reads take both `session_id` and `str(user_id)` so users cannot access each other's sessions.

---

## Creating Migrations

### Step 1: Create Migration File

Create `alembic/versions/NNN_description.py`:

```python
"""Add entities table.

Revision ID: 009_add_entities
Revises: 008_naive_utc_datetimes
Create Date: 2026-02-01

This migration adds the entities table for <feature description>.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "009_add_entities"
down_revision: Union[str, None] = "008_naive_utc_datetimes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create entities table."""
    op.create_table(
        "entities",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("value", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("timezone('utc', now())"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("timezone('utc', now())"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_entities_user_id",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "value IS NULL OR (value >= 0 AND value <= 100)",
            name="chk_entity_value",
        ),
    )

    # Create indexes
    op.create_index("idx_entities_user_id", "entities", ["user_id"], unique=False)
    op.create_index("idx_entities_name", "entities", ["name"], unique=False)


def downgrade() -> None:
    """Drop entities table."""
    op.drop_index("idx_entities_name", table_name="entities")
    op.drop_index("idx_entities_user_id", table_name="entities")
    op.drop_table("entities")
```

### Migration Conventions

| Convention | Details |
|------------|---------|
| Naming | Sequential numbering: `001_`, `002_`, ... (currently `001`-`008`; next is `009_`) |
| down_revision | Must reference the previous migration's `revision` string, which is not always the filename (file `006_add_oauth_state_linking_fields.py` has revision `006_oauth_linking`) |
| UUID columns | Use `sa.UUID()` with `server_default=sa.text("gen_random_uuid()")` |
| Timestamps | New migrations use naive UTC `sa.DateTime()` (`TIMESTAMP WITHOUT TIME ZONE`) with `server_default=sa.text("timezone('utc', now())")` (ADR-0010; migration 008 converted the earlier `timezone=True` columns) |
| Foreign keys | Name pattern: `fk_<table>_<column>`, always include `ondelete` |
| Constraints | Existing names: `chk_year`, `chk_rating`, `uq_user_movie`; use `chk_<field>` / `uq_<fields>` |
| Indexes | Create for all foreign keys and frequently queried columns |
| downgrade() | Must reverse all changes in upgrade() |
| Backward compatibility | The deploy workflow applies migrations before publishing new code, so the previous code keeps running against the new schema. Expand now, contract in a later release: add nullable columns/tables first, and drop or rename only after no running code uses them |

### Running Migrations

```bash
# Run from the repo root (alembic.ini lives there; DATABASE_URL comes from .env / settings)
# Apply migrations
alembic upgrade head

# Create new migration (auto-generate)
alembic revision --autogenerate -m "description"

# Rollback one migration
alembic downgrade -1

# See current revision
alembic current

# See migration history
alembic history
```

---

## Adding Tests

### Step 1: Create Test File

Create `tests/test_<entities>.py`:

```python
"""Tests for entities endpoints.

These tests verify the entities functionality including:
- Creating entities
- Listing entities with pagination
- Getting single entity
- Updating entities
- Deleting entities (with trailing slash)
- Authorization checks

NOTE: All URLs must include trailing slashes. See root CLAUDE.md.
"""

import pytest
from httpx import AsyncClient


class TestCreateEntity:
    """Tests for POST /api/v1/entities/ endpoint."""

    @pytest.mark.asyncio
    async def test_create_entity_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test successful entity creation."""
        response = await client.post(
            "/api/v1/entities/",  # Trailing slash required
            json={
                "name": "Test Entity",
                "value": 50,
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Entity"
        assert data["value"] == 50
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_entity_without_auth_returns_401(
        self, client: AsyncClient
    ):
        """Test that creating entity without auth returns 401."""
        response = await client.post(
            "/api/v1/entities/",
            json={"name": "Test"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_entity_invalid_value_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that invalid value returns 422 validation error."""
        response = await client.post(
            "/api/v1/entities/",
            json={
                "name": "Test",
                "value": 999,  # Out of range
            },
            headers=auth_headers,
        )

        assert response.status_code == 422


class TestListEntities:
    """Tests for GET /api/v1/entities/ endpoint."""

    @pytest.mark.asyncio
    async def test_list_entities_empty(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test listing entities when none exist."""
        response = await client.get(
            "/api/v1/entities/",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["limit"] == 20
        assert data["offset"] == 0

    @pytest.mark.asyncio
    async def test_list_entities_with_pagination(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test listing entities with pagination params."""
        # Create some entities first
        for i in range(5):
            await client.post(
                "/api/v1/entities/",
                json={"name": f"Entity {i}"},
                headers=auth_headers,
            )

        response = await client.get(
            "/api/v1/entities/",
            params={"limit": 2, "offset": 1},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["limit"] == 2
        assert data["offset"] == 1


class TestDeleteEntity:
    """Tests for DELETE /api/v1/entities/{entity_id}/ endpoint."""

    @pytest.mark.asyncio
    async def test_delete_entity_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test successful entity deletion with trailing slash."""
        # Create entity first
        create_response = await client.post(
            "/api/v1/entities/",
            json={"name": "To Delete"},
            headers=auth_headers,
        )
        entity_id = create_response.json()["id"]

        # Delete with trailing slash (required)
        delete_response = await client.delete(
            f"/api/v1/entities/{entity_id}/",
            headers=auth_headers,
        )

        assert delete_response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_other_user_entity_returns_403(
        self, client: AsyncClient
    ):
        """Test deleting another user's entity returns 403."""
        # Create first user and entity
        user1_response = await client.post(
            "/api/v1/auth/register",
            json={"email": "user1@test.com", "password": "password123"},
        )
        user1_token = user1_response.json()["access_token"]
        user1_headers = {"Authorization": f"Bearer {user1_token}"}

        entity_response = await client.post(
            "/api/v1/entities/",
            json={"name": "User1 Entity"},
            headers=user1_headers,
        )
        entity_id = entity_response.json()["id"]

        # Create second user
        user2_response = await client.post(
            "/api/v1/auth/register",
            json={"email": "user2@test.com", "password": "password123"},
        )
        user2_token = user2_response.json()["access_token"]
        user2_headers = {"Authorization": f"Bearer {user2_token}"}

        # Try to delete as user2
        response = await client.delete(
            f"/api/v1/entities/{entity_id}/",
            headers=user2_headers,
        )

        assert response.status_code == 403


class TestFullEntityFlow:
    """Integration tests for complete entity flows."""

    @pytest.mark.asyncio
    async def test_create_list_update_delete_flow(
        self, client: AsyncClient
    ):
        """Test complete CRUD flow for entities."""
        # Register user
        register_response = await client.post(
            "/api/v1/auth/register",
            json={"email": "flow@test.com", "password": "password123"},
        )
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create
        create_response = await client.post(
            "/api/v1/entities/",
            json={"name": "Flow Entity", "value": 25},
            headers=headers,
        )
        assert create_response.status_code == 201
        entity_id = create_response.json()["id"]

        # List
        list_response = await client.get(
            "/api/v1/entities/",
            headers=headers,
        )
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 1

        # Update
        update_response = await client.put(
            f"/api/v1/entities/{entity_id}/",
            json={"name": "Updated Entity"},
            headers=headers,
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Updated Entity"

        # Delete
        delete_response = await client.delete(
            f"/api/v1/entities/{entity_id}/",
            headers=headers,
        )
        assert delete_response.status_code == 204

        # Verify deleted
        list_response = await client.get(
            "/api/v1/entities/",
            headers=headers,
        )
        assert list_response.json()["total"] == 0
```

### Test Conventions

| Convention | Details |
|------------|---------|
| Class organization | Group by endpoint: `TestCreate*`, `TestList*`, `TestDelete*`, `TestFull*Flow` |
| Fixtures | Use `client`, `auth_headers`, `test_user`, `test_movie` from `tests/conftest.py` (`test_user` is `test@example.com` created through `/register`; `test_movie` is created through `POST /movies/`) |
| Assertions | Check status code first, then response body |
| Auth tests | Always test 401 (no auth) and 403 (wrong user) cases |
| Validation tests | Test 422 for invalid input |
| Flow tests | Test complete user journeys |
| Login tests | Use `data={}` (form), NOT `json={}` for /login |

> **Important:** All test URLs must include trailing slashes. See the [root CLAUDE.md](../CLAUDE.md) for details.

### Running Tests

Run from the repo root using the project virtualenv (`pytest.ini` sets `asyncio_mode = auto`, `testpaths = tests`):

```bash
# Run all tests
venv/bin/pytest

# Run with verbose output
venv/bin/pytest -v

# Run specific test file
venv/bin/pytest tests/test_rankings.py

# Run specific test class
venv/bin/pytest tests/test_rankings.py::TestCreateRanking

# Run specific test
venv/bin/pytest tests/test_rankings.py::TestCreateRanking::test_create_ranking_success
```

Install test dependencies with `pip install -r requirements-dev.txt`. Coverage (`--cov=app`) needs `pytest-cov`, which is not in `requirements-dev.txt`.

---

## Type Annotations and Dependencies

### Common Imports

```python
# FastAPI
from fastapi import APIRouter, HTTPException, Query, Response, status, Depends
from fastapi.security import OAuth2PasswordRequestForm

# SQLAlchemy
from sqlalchemy import func, select, text
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.ext.asyncio import AsyncSession

# Pydantic
from pydantic import BaseModel, ConfigDict, Field, EmailStr

# Typing
from typing import Annotated, Optional, List
from datetime import datetime, timezone
from uuid import UUID

# App-specific
from app.database import DbSession, Base
from app.dependencies import CurrentUser
from app.config import settings
```

### Type Aliases (from app/database.py and app/dependencies.py)

```python
# Database session dependency - use this in all routers
DbSession = Annotated[AsyncSession, Depends(get_db)]

# Current authenticated user - use this for protected endpoints
CurrentUser = Annotated[User, Depends(get_current_user)]
```

`get_db` commits after the request handler returns successfully and rolls back on an exception. Routers should `flush()` (never `commit()`) and let the dependency commit.

---

## Common Patterns and Utilities

### DateTime Handling (Naive UTC)

> **Note:** See the [root CLAUDE.md](../CLAUDE.md) for the datetime handling strategy. This section covers the backend implementation.

The database stores naive UTC datetimes. Always convert timezone-aware input:

```python
# Shared helpers live in app/utils/time.py (ADR-0010); never define them per router
from app.utils.time import to_naive_utc, utc_now_naive

# Usage in router (as in rankings.py)
rated_at = to_naive_utc(ranking_data.rated_at) or utc_now_naive()
```

### Database Operations Pattern

```python
# Create
new_entity = Entity(field=value)
db.add(new_entity)
await db.flush()
await db.refresh(new_entity)

# Read single
result = await db.execute(select(Entity).where(Entity.id == entity_id))
entity = result.scalar_one_or_none()

# Read with relationship
result = await db.execute(
    select(Entity)
    .options(joinedload(Entity.user))
    .where(Entity.id == entity_id)
)
entity = result.scalar_one_or_none()

# Read list with pagination
result = await db.execute(
    select(Entity)
    .where(Entity.user_id == current_user.id)
    .order_by(Entity.created_at.desc())
    .limit(limit)
    .offset(offset)
)
entities = result.scalars().all()

# Count
count_result = await db.execute(
    select(func.count()).where(Entity.user_id == current_user.id)
)
total = count_result.scalar_one()

# Update (modify object attributes, then flush)
entity.name = new_name
await db.flush()
await db.refresh(entity)

# Delete
await db.delete(entity)
await db.flush()
```

### Error Handling Pattern

```python
# Not found
if entity is None:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Entity not found",
    )

# Forbidden (authorization)
if entity.user_id != current_user.id:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized to access this entity",
    )

# Conflict (duplicate)
if existing is not None:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Entity already exists",
    )
```

### Security Utilities (from app/utils/security.py)

```python
from app.utils.security import (
    get_password_hash,    # Hash password for storage
    verify_password,      # Check password against hash
    create_access_token,  # Generate JWT token
    decode_token,         # Validate and decode JWT
    TokenError,           # Base exception
    TokenExpiredError,    # Token expired
    TokenInvalidError,    # Token invalid
)
```

---

## Logging and Request IDs

Logging is configured in `app/observability/` (called from `app/main.py`; tests install the same behavior via `install_observability(app)` in `tests/conftest.py`).

- `configure_logging()` emits one JSON object per line: `timestamp`, `level`, `logger`, `message`, `request_id`, plus any `extra={...}` fields. Existing `logger.info(f"...")` calls keep working.
- `RequestIdMiddleware` accepts a valid inbound `X-Request-ID` (8-64 chars of `A-Za-z0-9._-`), else API Gateway's request id, else generates one. It returns `X-Request-ID` on every response and logs one `app.access` record per request: `method`, `path` (never the query string), `status`, `duration_ms`, and `user_id` when `get_current_user` ran.
- Unhandled exceptions are logged once as `unhandled_exception` (with `exception_type` and traceback) and return `{"detail": "Internal server error"}` with `X-Request-ID`. `HTTPException` and validation errors use FastAPI's defaults.
- Never log request bodies, `Authorization`/`Cookie` headers, tokens, or URLs with query strings.

## Important Gotchas

> **Note:** For trailing slashes, datetime handling, and HTTP status codes, see the [root CLAUDE.md](../CLAUDE.md). This section covers backend-specific gotchas.

### 1. Login Uses Form Data, Not JSON

The `/login` endpoint uses `OAuth2PasswordRequestForm` which requires `application/x-www-form-urlencoded`:

```python
# In tests - use data=, not json=
response = await client.post(
    "/api/v1/auth/login",
    data={"username": email, "password": password},  # CORRECT
    # json={"username": email, "password": password},  # WRONG
)
```

### 2. Always Check Ownership

For user-specific resources, always verify ownership before allowing operations:

```python
if entity.user_id != current_user.id:
    raise HTTPException(status_code=403, detail="Not authorized")
```

### 3. Use flush() and refresh() for Created/Updated Records

To get database-generated values (id, timestamps):

```python
db.add(new_entity)
await db.flush()      # Write to DB to get generated values
await db.refresh(new_entity)  # Load generated values into object
return new_entity
```

### 4. Unique Results with joinedload

When using `joinedload` with collections, call `.unique()`:

```python
result = await db.execute(
    select(Entity)
    .options(joinedload(Entity.items))
    .where(...)
)
entities = result.scalars().unique().all()  # .unique() is important
```

### 5. SQLite Test Compatibility

Tests use a per-test temporary SQLite file (`sqlite+aiosqlite`), which doesn't support PostgreSQL's `gen_random_uuid()`. `tests/conftest.py` handles this by patching `id`, `user_id` and `movie_id` columns to a `SQLiteUUID` type and generating UUIDs in a `before_flush` hook, but only for `User`, `Movie`, `Ranking` and `OAuthState`. If you add a model or UUID foreign key with a different name, update `patch_uuid_columns()` and the hook in `conftest.py`. The test app in `conftest.py` also registers routers by hand, so add new routers there too.

### 6. Import Models Before Migrations

The alembic `env.py` imports models to ensure metadata is registered:

```python
from app import models  # noqa: F401
```

Always ensure new models are exported from `app/models/__init__.py`. Run `alembic` from the repo root.

---

## Quick Reference Checklist

When adding a new feature:

- [ ] Review [root CLAUDE.md](../CLAUDE.md) for project-wide conventions
- [ ] Create model in `app/models/<entity>.py`
- [ ] Export model from `app/models/__init__.py`
- [ ] Add relationships to related models (e.g., User)
- [ ] Create schemas in `app/schemas/<entity>.py`
- [ ] Export schemas from `app/schemas/__init__.py`
- [ ] Create router in `app/routers/<entities>.py`
- [ ] Register router in `app/main.py` with prefix `/api/v1/<entities>` (and in the test app in `tests/conftest.py`)
- [ ] Create migration in `alembic/versions/NNN_description.py`
- [ ] Create tests in `tests/test_<entities>.py`
- [ ] All endpoints have trailing slashes
- [ ] All protected endpoints use `CurrentUser` dependency
- [ ] All database operations use `DbSession` dependency
- [ ] Authorization checks for user-owned resources
- [ ] Schema docstrings document response shapes for frontend
- [ ] Tests cover create, read, update, delete, auth, and validation
