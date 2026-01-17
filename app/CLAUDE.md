# Backend Development Guide

This document provides FastAPI/Python development guidance for the Movie Ranking API backend.

> **Important:** Before reading this guide, review the [root CLAUDE.md](../CLAUDE.md) for project-wide conventions including trailing slashes, datetime handling, HTTP status codes, and API contract verification. This guide focuses on backend-specific patterns and implementation details.

## Project Structure

```
app/
  __init__.py
  main.py              # FastAPI app, lifespan, router registration
  config.py            # Settings via pydantic-settings
  database.py          # Async SQLAlchemy engine, session, Base, DbSession
  dependencies.py      # Auth dependencies (CurrentUser, get_current_user)
  models/
    __init__.py        # Re-exports all models
    user.py            # User model
    movie.py           # Movie model
    ranking.py         # Ranking model (with relationships)
  schemas/
    __init__.py        # Re-exports all schemas
    user.py            # UserCreate, UserResponse
    movie.py           # MovieCreate, MovieResponse, MovieBrief
    ranking.py         # RankingCreate, RankingResponse, RankingWithMovie, RankingListResponse
    token.py           # Token schema
  routers/
    __init__.py
    auth.py            # /register, /login endpoints
    movies.py          # Movie CRUD
    rankings.py        # Ranking CRUD with pagination
  utils/
    __init__.py
    security.py        # Password hashing, JWT encode/decode
alembic/
  env.py               # Async migration config
  versions/
    001_initial_schema.py
tests/
  __init__.py
  conftest.py          # Fixtures: client, test_user, auth_headers, test_movie
  test_auth.py
  test_rankings.py
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
        onupdate=datetime.utcnow,
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
from app.models.ranking import Ranking
from app.models.user import User

__all__ = ["Entity", "Movie", "Ranking", "User"]  # Add to list
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
| List responses | Always include `items`, `total`, `limit`, `offset` for pagination |

---

## Frontend API Contract Documentation

> **Note:** See the [root CLAUDE.md](../CLAUDE.md) for the complete API contract verification requirements. This section covers backend-specific documentation patterns.

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
| Direct response | Single item CRUD operations | `MovieResponse` for GET /movies/{id}/ |
| List wrapper | Paginated collections | `RankingListResponse` for GET /rankings/ |
| Search wrapper | Search results with metadata | `TMDBSearchResponse` with query echo |

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


def to_naive_utc(dt: datetime | None) -> datetime | None:
    """Convert a datetime to naive UTC datetime for database storage.

    See root CLAUDE.md for datetime handling strategy.
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


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

---

## Creating Migrations

### Step 1: Create Migration File

Create `alembic/versions/NNN_description.py`:

```python
"""Add entities table.

Revision ID: 002_add_entities
Revises: 001_initial_schema
Create Date: 2024-01-15

This migration adds the entities table for <feature description>.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "002_add_entities"
down_revision: Union[str, None] = "001_initial_schema"
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
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
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
| Naming | Sequential numbering: `001_`, `002_`, etc. |
| down_revision | Must reference previous migration |
| UUID columns | Use `sa.UUID()` with `server_default=sa.text("gen_random_uuid()")` |
| Timestamps | Use `sa.DateTime(timezone=True)` with `CURRENT_TIMESTAMP` |
| Foreign keys | Name pattern: `fk_<table>_<column>`, always include `ondelete` |
| Constraints | Name pattern: `chk_<table>_<field>` or `uq_<table>_<fields>` |
| Indexes | Create for all foreign keys and frequently queried columns |
| downgrade() | Must reverse all changes in upgrade() |

### Running Migrations

```bash
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
| Fixtures | Use `client`, `auth_headers`, `test_user`, `test_movie` from conftest.py |
| Assertions | Check status code first, then response body |
| Auth tests | Always test 401 (no auth) and 403 (wrong user) cases |
| Validation tests | Test 422 for invalid input |
| Flow tests | Test complete user journeys |
| Login tests | Use `data={}` (form), NOT `json={}` for /login |

> **Important:** All test URLs must include trailing slashes. See the [root CLAUDE.md](../CLAUDE.md) for details.

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_entities.py

# Run specific test class
pytest tests/test_entities.py::TestCreateEntity

# Run specific test
pytest tests/test_entities.py::TestCreateEntity::test_create_entity_success

# Run with coverage
pytest --cov=app
```

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

---

## Common Patterns and Utilities

### DateTime Handling (Naive UTC)

> **Note:** See the [root CLAUDE.md](../CLAUDE.md) for the datetime handling strategy. This section covers the backend implementation.

The database stores naive UTC datetimes. Always convert timezone-aware input:

```python
from datetime import datetime, timezone

def to_naive_utc(dt: datetime | None) -> datetime | None:
    """Convert a datetime to naive UTC datetime for database storage."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt

# Usage in router
entity.timestamp = to_naive_utc(data.timestamp) or datetime.utcnow()
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

Tests use SQLite which doesn't support PostgreSQL's `gen_random_uuid()`. The conftest.py handles this with custom UUID generation, but be aware if adding new UUID columns.

### 6. Import Models Before Migrations

The alembic `env.py` imports models to ensure metadata is registered:

```python
from app import models  # noqa: F401
```

Always ensure new models are exported from `app/models/__init__.py`.

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
- [ ] Register router in `app/main.py` with prefix `/api/v1/<entities>`
- [ ] Create migration in `alembic/versions/NNN_description.py`
- [ ] Create tests in `tests/test_<entities>.py`
- [ ] All endpoints have trailing slashes
- [ ] All protected endpoints use `CurrentUser` dependency
- [ ] All database operations use `DbSession` dependency
- [ ] Authorization checks for user-owned resources
- [ ] Schema docstrings document response shapes for frontend
- [ ] Tests cover create, read, update, delete, auth, and validation
