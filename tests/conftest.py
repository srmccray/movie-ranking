"""Pytest fixtures and configuration for Movie Ranking API tests.

This configuration uses SQLite as the test database with adaptations
to handle PostgreSQL-specific features like UUID columns.
"""

import asyncio
import os
import sqlite3
import tempfile
from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID, uuid4

# Set test environment variables BEFORE importing app modules
# This ensures settings can be loaded during test discovery
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing")
os.environ.setdefault("TMDB_API_KEY", "test-tmdb-api-key")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, String, TypeDecorator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.database import Base, get_db


# Register UUID type adapter for SQLite
sqlite3.register_adapter(UUID, lambda u: str(u))
sqlite3.register_converter("UUID", lambda b: UUID(b.decode()))


class SQLiteUUID(TypeDecorator):
    """Platform-independent UUID type that works with SQLite.

    Uses String storage on SQLite but handles UUID objects transparently.
    """
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if isinstance(value, UUID):
                return str(value)
            return value
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            if not isinstance(value, UUID):
                return UUID(value)
            return value
        return value


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


def patch_uuid_columns():
    """Patch UUID columns to use SQLite-compatible type."""
    from app.models.user import User
    from app.models.movie import Movie
    from app.models.ranking import Ranking

    # Override the column type for id columns to use String in SQLite
    # This is done at the metadata level
    for model in [User, Movie, Ranking]:
        if hasattr(model, "__table__"):
            for column in model.__table__.columns:
                if column.name == "id":
                    column.type = SQLiteUUID()
                elif column.name in ("user_id", "movie_id"):
                    column.type = SQLiteUUID()


@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing API endpoints."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from app.routers import auth, movies, rankings

    # Patch UUID columns for SQLite compatibility
    patch_uuid_columns()

    # Create a temporary database file for this test
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    test_db_url = f"sqlite+aiosqlite:///{db_path}"

    # Create engine for this test
    engine = create_async_engine(
        test_db_url,
        echo=False,
        connect_args={
            "check_same_thread": False,
        },
    )

    # Add SQLite function for UUID generation
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_functions(dbapi_connection, connection_record):
        import uuid
        dbapi_connection.create_function("gen_random_uuid", 0, lambda: str(uuid.uuid4()))

    # Generate UUID on Python side before insert
    @event.listens_for(Session, "before_flush")
    def generate_uuid_before_flush(session, flush_context, instances):
        from app.models.user import User
        from app.models.movie import Movie
        from app.models.ranking import Ranking

        for obj in session.new:
            if isinstance(obj, (User, Movie, Ranking)):
                if obj.id is None:
                    obj.id = uuid4()

    # Create session maker
    session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create test app
    test_app = FastAPI()
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    test_app.include_router(auth.router, prefix="/api/v1/auth")
    test_app.include_router(movies.router, prefix="/api/v1/movies")
    test_app.include_router(rankings.router, prefix="/api/v1/rankings")

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    test_app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Cleanup
    test_app.dependency_overrides.clear()
    await engine.dispose()
    try:
        os.unlink(db_path)
    except Exception:
        pass


@pytest_asyncio.fixture
async def test_user(client: AsyncClient) -> dict[str, Any]:
    """Create a test user via the API and return user data with token."""
    email = "test@example.com"
    password = "testpassword123"

    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )

    if response.status_code != 201:
        raise RuntimeError(f"Failed to create test user: {response.json()}")

    data = response.json()

    return {
        "email": email,
        "password": password,
        "access_token": data["access_token"],
    }


@pytest_asyncio.fixture
async def auth_headers(test_user: dict[str, Any]) -> dict[str, str]:
    """Return authorization headers for authenticated requests."""
    return {"Authorization": f"Bearer {test_user['access_token']}"}


@pytest_asyncio.fixture
async def test_movie(client: AsyncClient, auth_headers: dict[str, str]) -> dict[str, Any]:
    """Create a test movie via the API and return movie data."""
    response = await client.post(
        "/api/v1/movies/",
        json={"title": "Test Movie", "year": 2024},
        headers=auth_headers,
    )

    if response.status_code != 201:
        raise RuntimeError(f"Failed to create test movie: {response.json()}")

    data = response.json()

    return {
        "movie_id": data["id"],
        "title": data["title"],
        "year": data["year"],
    }
