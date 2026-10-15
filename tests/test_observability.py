"""Observability tests: request ids, access logs and the unhandled-exception handler."""

import json
import logging
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.observability.logging_config import JsonFormatter


class _Capture(logging.Handler):
    """Collect log records as the JSON the production formatter would emit."""

    def __init__(self) -> None:
        super().__init__()
        self.setFormatter(JsonFormatter())
        self.entries: list[dict[str, Any]] = []

    def emit(self, record: logging.LogRecord) -> None:
        if not record.name.startswith("app"):
            return  # ignore the test client's own httpx request logging
        self.entries.append(json.loads(self.format(record)))


@pytest.fixture
def captured() -> Iterator[_Capture]:
    handler = _Capture()
    root = logging.getLogger()
    old_level = root.level
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    yield handler
    root.removeHandler(handler)
    root.setLevel(old_level)


def _access(captured: _Capture) -> list[dict[str, Any]]:
    return [e for e in captured.entries if e["logger"] == "app.access"]


@pytest.mark.asyncio
async def test_response_has_generated_request_id(client: AsyncClient, captured: _Capture) -> None:
    response = await client.get("/api/v1/movies/")
    assert response.headers["X-Request-ID"]
    assert _access(captured)[0]["request_id"] == response.headers["X-Request-ID"]


@pytest.mark.asyncio
async def test_valid_inbound_request_id_is_echoed(client: AsyncClient) -> None:
    rid = str(uuid.uuid4())
    response = await client.get("/api/v1/movies/", headers={"X-Request-ID": rid})
    assert response.headers["X-Request-ID"] == rid


@pytest.mark.asyncio
async def test_invalid_inbound_request_id_is_replaced(client: AsyncClient) -> None:
    response = await client.get("/api/v1/movies/", headers={"X-Request-ID": "bad id with junk"})
    assert response.headers["X-Request-ID"] != "bad id with junk"


@pytest.mark.asyncio
async def test_access_log_has_fields_and_no_secrets(
    client: AsyncClient, test_user: dict[str, Any], captured: _Capture
) -> None:
    captured.entries.clear()
    token = test_user["access_token"]
    response = await client.get(
        "/api/v1/rankings/?secretquery=1&code=oauthcode",
        headers={"Authorization": f"Bearer {token}", "Cookie": "session=cookiesecret"},
    )
    records = _access(captured)
    assert len(records) == 1
    record = records[0]
    assert record["request_id"] == response.headers["X-Request-ID"]
    assert record["method"] == "GET"
    assert record["path"] == "/api/v1/rankings/"
    assert record["status"] == response.status_code
    assert isinstance(record["duration_ms"], (int, float))
    assert record["user_id"]
    dumped = json.dumps(captured.entries)
    for secret in ("secretquery", "oauthcode", "cookiesecret", "Authorization", token):
        assert secret not in dumped


@pytest.mark.asyncio
async def test_request_body_is_never_logged(client: AsyncClient, captured: _Capture) -> None:
    await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "hunter2-body-secret"},
    )
    assert "hunter2-body-secret" not in json.dumps(captured.entries)


@pytest.mark.asyncio
async def test_unhandled_exception_logged_once_with_request_id(
    client: AsyncClient, captured: _Capture
) -> None:
    app: FastAPI = client._transport.app  # type: ignore[attr-defined]

    @app.get("/boom-test/")
    async def boom() -> None:
        raise ValueError("kaboom")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        response = await c.get("/boom-test/")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    rid = response.headers["X-Request-ID"]
    errors = [e for e in captured.entries if e["message"] == "unhandled_exception"]
    assert len(errors) == 1
    assert errors[0]["request_id"] == rid
    assert errors[0]["exception_type"] == "ValueError"
    access = _access(captured)
    assert access[-1]["status"] == 500 and access[-1]["request_id"] == rid
