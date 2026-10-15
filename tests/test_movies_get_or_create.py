"""Tests for POST /api/v1/movies/ get-or-create by tmdb_id (TASK-0023)."""

from datetime import datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.models.movie import Movie
from app.services.movies import find_movie_by_tmdb_id
from tests.import_amazon_helpers import create_mock_tmdb_result, create_test_csv


async def _register_second_user(client: AsyncClient) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "second@example.com", "password": "testpassword123"},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


class TestGetOrCreateMovie:
    @pytest.mark.asyncio
    async def test_same_tmdb_id_twice_returns_201_then_200_same_id(
        self, client: AsyncClient, auth_headers: dict
    ):
        payload = {"title": "The Matrix", "year": 1999, "tmdb_id": 603}
        first = await client.post("/api/v1/movies/", json=payload, headers=auth_headers)
        second = await client.post("/api/v1/movies/", json=payload, headers=auth_headers)

        assert first.status_code == 201
        assert second.status_code == 200
        assert first.json()["id"] == second.json()["id"]

    @pytest.mark.asyncio
    async def test_two_users_share_one_movie(
        self, client: AsyncClient, auth_headers: dict
    ):
        other = await _register_second_user(client)
        payload = {"title": "The Matrix", "year": 1999, "tmdb_id": 603}
        first = await client.post("/api/v1/movies/", json=payload, headers=auth_headers)
        second = await client.post("/api/v1/movies/", json=payload, headers=other)

        assert (first.status_code, second.status_code) == (201, 200)
        assert first.json()["id"] == second.json()["id"]

    @pytest.mark.asyncio
    async def test_existing_movie_backfills_only_null_fields(
        self, client: AsyncClient, auth_headers: dict
    ):
        first = await client.post(
            "/api/v1/movies/",
            json={"title": "Original", "tmdb_id": 603, "vote_average": 8.0},
            headers=auth_headers,
        )
        second = await client.post(
            "/api/v1/movies/",
            json={
                "title": "Changed",
                "tmdb_id": 603,
                "vote_average": 1.0,
                "vote_count": 100,
                "genre_ids": [28],
                "original_language": "en",
                "runtime": 136,
                "release_date": "1999-03-31",
            },
            headers=auth_headers,
        )

        assert first.status_code == 201
        assert second.status_code == 200
        body = second.json()
        assert body["title"] == "Original"
        assert body["vote_average"] == 8.0
        assert body["vote_count"] == 100
        assert body["genre_ids"] == [28]
        assert body["original_language"] == "en"
        assert body["runtime"] == 136
        assert body["release_date"] == "1999-03-31"

    @pytest.mark.asyncio
    async def test_null_tmdb_id_always_creates(
        self, client: AsyncClient, auth_headers: dict
    ):
        payload = {"title": "Home Movie", "year": 2020}
        first = await client.post("/api/v1/movies/", json=payload, headers=auth_headers)
        second = await client.post("/api/v1/movies/", json=payload, headers=auth_headers)

        assert first.status_code == 201
        assert second.status_code == 201
        assert first.json()["id"] != second.json()["id"]


class TestFindMovieByTmdbIdWithDuplicates:
    @pytest.mark.asyncio
    async def test_returns_oldest_when_duplicates_exist(self, client: AsyncClient):
        # `client` fixture applies the SQLite UUID patches the models need.
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        maker = async_sessionmaker(engine, expire_on_commit=False)
        oldest_id = uuid4()
        async with maker() as session:
            session.add(
                Movie(id=uuid4(), title="Newer", tmdb_id=7, created_at=datetime(2024, 2, 1))
            )
            session.add(
                Movie(id=oldest_id, title="Older", tmdb_id=7, created_at=datetime(2024, 1, 1))
            )
            await session.commit()

            found = await find_movie_by_tmdb_id(session, 7)

        await engine.dispose()
        assert found is not None
        assert found.id == oldest_id


class TestImportReusesMovie:
    @pytest.mark.asyncio
    async def test_import_add_reuses_movie_created_via_post(
        self, client: AsyncClient, auth_headers: dict
    ):
        created = await client.post(
            "/api/v1/movies/",
            json={"title": "Test Movie", "year": 2024, "tmdb_id": 12345},
            headers=auth_headers,
        )
        csv_file = create_test_csv(
            [{"Type": "Movie", "Title": "Test Movie", "Date Watched": "2024-01-15"}]
        )
        with patch("app.routers.import_amazon.matching.TMDBService") as mock_cls:
            inst = AsyncMock()
            inst.__aenter__.return_value = inst
            inst.__aexit__.return_value = None
            inst.search_movies.return_value = [
                create_mock_tmdb_result(
                    tmdb_id=12345, title="Test Movie", year=2024, poster_url=None, overview=None
                )
            ]
            mock_cls.return_value = inst
            upload = await client.post(
                "/api/v1/import/amazon-prime/upload/",
                files={"file": ("test.csv", csv_file, "text/csv")},
                headers=auth_headers,
            )
        session_id = upload.json()["session_id"]

        with patch("app.routers.import_amazon.review.get_movie_details") as details:
            details.return_value = AsyncMock(runtime=120)
            added = await client.post(
                f"/api/v1/import/amazon-prime/session/{session_id}/movie/0/add/",
                json={"rating": 4},
                headers=auth_headers,
            )

        assert added.status_code == 201
        assert added.json()["movie_id"] == created.json()["id"]
