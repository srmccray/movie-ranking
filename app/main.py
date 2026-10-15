"""FastAPI application entry point for the Movie Ranking API."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.database import engine, get_db
from app.observability import configure_logging, install_observability
from app.routers import analytics, auth, google_auth, import_amazon, movies, rankings

# Configure structured JSON logging
configure_logging(logging.DEBUG if settings.DEBUG else logging.INFO)
logger = logging.getLogger(__name__)

# CORS origins configuration
# Default allows React development server, production origin added via CORS_ORIGIN env var
ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

# Add production origin if CORS_ORIGIN environment variable is set
if os.environ.get("CORS_ORIGIN"):
    ALLOWED_ORIGINS.append(os.environ["CORS_ORIGIN"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events.

    On startup:
        - Verifies database connection is working

    On shutdown:
        - Disposes of the database engine connection pool

    Args:
        app: The FastAPI application instance.

    Yields:
        Control back to the application after startup tasks complete.
    """
    # Startup: Verify database connection
    logger.info("Starting Movie Ranking API...")
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection verified successfully")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

    yield

    # Shutdown: Clean up database connections
    logger.info("Shutting down Movie Ranking API...")
    await engine.dispose()
    logger.info("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title="Movie Ranking API",
    description=(
        "A RESTful API for ranking and managing your favorite movies. "
        "Features include user authentication, movie management, and personal rankings."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request id, access logging and unhandled-exception handler
install_observability(app)

# Include routers with API versioning
app.include_router(auth.router, prefix="/api/v1/auth")
app.include_router(google_auth.router, prefix="/api/v1/auth")
app.include_router(movies.router, prefix="/api/v1/movies")
app.include_router(rankings.router, prefix="/api/v1/rankings")
app.include_router(analytics.router, prefix="/api/v1/analytics")
app.include_router(import_amazon.router, prefix="/api/v1/import")


_DEEP_HEALTH_TIMEOUT_SECONDS = 2.0


async def _probe_database(request: Request) -> None:
    """Run ``SELECT 1`` through the ``get_db`` provider (honours dependency overrides)."""
    provider = request.app.dependency_overrides.get(get_db, get_db)
    async with asynccontextmanager(provider)() as session:
        await session.execute(text("SELECT 1"))


@app.get(
    "/health",
    tags=["health"],
    summary="Health check endpoint",
    response_model=dict[str, Any],
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "examples": {
                        "liveness": {
                            "summary": "Liveness (default, no database)",
                            "value": {"status": "healthy", "version": "1.0.0"},
                        },
                        "deep": {
                            "summary": "Readiness (?deep=true)",
                            "value": {"status": "healthy", "database": "ok"},
                        },
                    }
                }
            },
        },
        503: {
            "description": "Service is unhealthy (deep check only: database unreachable)",
            "content": {
                "application/json": {
                    "example": {"status": "unhealthy", "database": "unreachable"}
                }
            },
        },
    },
)
async def health_check(request: Request, deep: bool = False) -> JSONResponse:
    """Check the health status of the API.

    By default this is a liveness check that never touches the database.
    With ``deep=true`` it also runs ``SELECT 1`` (2 second timeout) and
    returns 503 when the database is unreachable.
    """
    if not deep:
        return JSONResponse({"status": "healthy", "version": "1.0.0"})
    try:
        await asyncio.wait_for(
            _probe_database(request), timeout=_DEEP_HEALTH_TIMEOUT_SECONDS
        )
    except Exception:
        logger.exception("Deep health check failed: database unreachable")
        return JSONResponse(
            {"status": "unhealthy", "database": "unreachable"}, status_code=503
        )
    return JSONResponse({"status": "healthy", "database": "ok"})


@app.get(
    "/",
    tags=["health"],
    summary="Root endpoint",
    response_model=dict[str, str],
)
async def root() -> dict[str, str]:
    """Root endpoint with API information.

    Returns:
        A dictionary with a welcome message and documentation link.
    """
    return {
        "message": "Welcome to the Movie Ranking API",
        "docs": "/docs",
    }
