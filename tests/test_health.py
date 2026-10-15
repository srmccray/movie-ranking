"""Health endpoint tests through the real application's HTTP boundary."""

from collections.abc import AsyncGenerator, Iterator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.database import get_db
from app.main import app


@pytest.fixture
def overrides() -> Iterator[dict[Any, Any]]:
    saved = dict(app.dependency_overrides)
    yield app.dependency_overrides
    app.dependency_overrides.clear()
    app.dependency_overrides.update(saved)


@pytest_asyncio.fixture
async def health_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


async def _broken_db() -> AsyncGenerator[AsyncSession, None]:
    raise RuntimeError("secret connection string")
    yield  # pragma: no cover


async def test_liveness_does_not_touch_database(overrides, health_client):
    overrides[get_db] = _broken_db
    response = await health_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "version": "1.0.0"}


async def test_deep_health_ok_when_database_up(overrides, health_client):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async def ok_db() -> AsyncGenerator[AsyncSession, None]:
        async with AsyncSession(engine) as session:
            yield session

    overrides[get_db] = ok_db
    response = await health_client.get("/health", params={"deep": "true"})
    await engine.dispose()
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "database": "ok"}


async def test_deep_health_503_when_database_unreachable(overrides, health_client):
    overrides[get_db] = _broken_db
    response = await health_client.get("/health", params={"deep": "true"})
    assert response.status_code == 503
    assert response.json() == {"status": "unhealthy", "database": "unreachable"}
    assert "secret" not in response.text
