"""Start the real FastAPI app against a throwaway SQLite database for e2e runs.

The models target PostgreSQL (UUID columns, gen_random_uuid()). The backend
pytest suite already runs them on SQLite by swapping the UUID column type and
generating ids in Python; this launcher applies the same adaptation, then
serves the unmodified `app.main:app` over HTTP. No application code is changed
and no production database is touched: the DATABASE_URL is forced to a
temporary file that is deleted on exit.

Usage (from repo root): venv/bin/python frontend/e2e/support/run_backend.py [port]
"""

import atexit
import os
import sys
import tempfile
import uuid

fd, DB_PATH = tempfile.mkstemp(prefix="movie-ranking-e2e-", suffix=".db")
os.close(fd)
atexit.register(lambda: os.path.exists(DB_PATH) and os.unlink(DB_PATH))

# Force isolation: override anything from .env or the caller's shell.
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{DB_PATH}"
os.environ["DEBUG"] = "false"
os.environ["SECRET_KEY"] = "e2e-only-secret-key"
os.environ["TMDB_API_KEY"] = "e2e-unused-tmdb-key"
os.environ["CORS_ORIGIN"] = "http://localhost:3100"

import asyncio  # noqa: E402

import uvicorn  # noqa: E402
from sqlalchemy import String, event  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from sqlalchemy.types import TypeDecorator  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.models.movie import Movie  # noqa: E402
from app.models.oauth_state import OAuthState  # noqa: E402
from app.models.ranking import Ranking  # noqa: E402
from app.models.user import User  # noqa: E402

MODELS = (User, Movie, Ranking, OAuthState)


class SQLiteUUID(TypeDecorator):
    """Store UUIDs as 36-char strings on SQLite."""

    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else str(value)

    def process_result_value(self, value, dialect):
        return None if value is None else uuid.UUID(str(value))


for model in MODELS:
    for column in model.__table__.columns:
        if column.name in ("id", "user_id", "movie_id"):
            column.type = SQLiteUUID()


@event.listens_for(Session, "before_flush")
def _assign_ids(session, flush_context, instances):
    for obj in session.new:
        if isinstance(obj, MODELS) and obj.id is None:
            obj.id = uuid.uuid4()


async def _create_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(_create_schema())
    from app.main import app

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8100
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
