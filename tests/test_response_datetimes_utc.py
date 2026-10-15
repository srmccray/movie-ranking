"""Response datetimes are always UTC-aware ISO 8601 (ADR-0010, TASK-0019)."""

import pytest
from httpx import AsyncClient

DT_FIELDS = ("rated_at", "created_at", "updated_at")


class TestResponseDatetimesUTC:
    @pytest.mark.asyncio
    async def test_rankings_list_datetimes_end_in_z(
        self, client: AsyncClient, auth_headers: dict, test_movie: dict
    ):
        await client.post(
            "/api/v1/rankings/",
            json={
                "movie_id": test_movie["movie_id"],
                "rating": 4,
                "rated_at": "2026-03-01T23:30:00Z",
            },
            headers=auth_headers,
        )
        response = await client.get("/api/v1/rankings/", headers=auth_headers)
        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["rated_at"] == "2026-03-01T23:30:00Z"
        for field in DT_FIELDS:
            assert item[field].endswith("Z")

    @pytest.mark.asyncio
    async def test_me_created_at_ends_in_z(
        self, client: AsyncClient, auth_headers: dict
    ):
        response = await client.get("/api/v1/auth/me/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["created_at"].endswith("Z")

    @pytest.mark.asyncio
    async def test_create_movie_created_at_ends_in_z(
        self, client: AsyncClient, auth_headers: dict
    ):
        response = await client.post(
            "/api/v1/movies/",
            json={"title": "UTC Movie", "year": 2020},
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["created_at"].endswith("Z")

    @pytest.mark.asyncio
    async def test_offset_request_serializes_to_same_utc_instant(
        self, client: AsyncClient, auth_headers: dict, test_movie: dict
    ):
        response = await client.post(
            "/api/v1/rankings/",
            json={
                "movie_id": test_movie["movie_id"],
                "rating": 3,
                "rated_at": "2026-03-02T04:30:00+05:00",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["rated_at"] == "2026-03-01T23:30:00Z"
