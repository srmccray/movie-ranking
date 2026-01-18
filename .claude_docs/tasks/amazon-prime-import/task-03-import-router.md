# Task 03: Import Router and Endpoints

**Feature:** amazon-prime-import
**Agent:** backend-implementation
**Status:** Not Started
**Blocked By:** 01, 02

---

## Objective

Create the FastAPI router with all import endpoints: CSV upload, session retrieval, add movie, skip movie, and cancel session. Implement TMDB matching with rate limiting and confidence scoring.

---

## Context

This is the core backend task that ties together the schemas, session storage, and CSV parser into functional API endpoints. The router handles file upload, orchestrates TMDB matching, and manages the import workflow state.

### Relevant FRD Sections
- FRD Section: "API Design" - All endpoint specifications
- FRD Section: "TMDB Matching Strategy" - Confidence calculation, rate limiting

### Relevant Refinement Notes
- Use TMDBService from existing codebase with batch delays
- Confidence = title_similarity * 0.6 + year_match * 0.4
- Rate limit: 1-second delay every 35 requests
- On TMDBRateLimitError: wait 2 seconds, retry once

---

## Scope

### In Scope
- Create `app/routers/import_amazon.py` with all endpoints
- Register router in `app/main.py`
- Implement TMDB matching with confidence scoring
- Implement rate limiting for batch TMDB lookups
- Check for already-ranked movies
- Create rankings using existing patterns

### Out of Scope
- Schema definitions (task-01)
- CSV parsing (task-02)
- Frontend components (task-05)

---

## Implementation Notes

### Key Files

| File | Action | Notes |
|------|--------|-------|
| `/Users/stephen/Projects/movie-ranking/app/routers/import_amazon.py` | Create | All import endpoints |
| `/Users/stephen/Projects/movie-ranking/app/main.py` | Modify | Register router |

### Patterns to Follow

- Router pattern: See `/Users/stephen/Projects/movie-ranking/app/routers/rankings.py`
- File upload: Use `UploadFile` from FastAPI
- TMDB service: See `/Users/stephen/Projects/movie-ranking/app/services/tmdb.py`
- Datetime conversion: Use `to_naive_utc()` pattern from rankings router

### API Endpoints

```
POST /api/v1/import/amazon-prime/upload/
  - Content-Type: multipart/form-data
  - Body: file (CSV file)
  - Response: ImportSessionResponse (201 Created)

GET /api/v1/import/amazon-prime/session/{session_id}/
  - Response: ImportSessionDetailResponse (200 OK)

POST /api/v1/import/amazon-prime/session/{session_id}/movie/{index}/add/
  - Body: ImportMovieAddRequest { "rating": 1-5, "rated_at": "ISO8601" }
  - Response: RankingResponse (201 Created)

POST /api/v1/import/amazon-prime/session/{session_id}/movie/{index}/skip/
  - Response: 204 No Content

DELETE /api/v1/import/amazon-prime/session/{session_id}/
  - Response: 204 No Content
```

### Implementation

```python
# app/routers/import_amazon.py

"""Amazon Prime import router for CSV upload and movie import workflow."""

import asyncio
import logging
from datetime import datetime, timezone
from difflib import SequenceMatcher
from uuid import UUID

from fastapi import APIRouter, HTTPException, UploadFile, status
from sqlalchemy import select

from app.database import DbSession
from app.dependencies import CurrentUser
from app.models.movie import Movie
from app.models.ranking import Ranking
from app.schemas.import_amazon import (
    ImportMovieAddRequest,
    ImportSessionDetailResponse,
    ImportSessionResponse,
    MatchedMovieItem,
    ParsedMovieItem,
    TMDBMatchResult,
)
from app.schemas.ranking import RankingResponse
from app.services.csv_parser import parse_amazon_prime_csv
from app.services.import_session import import_session_store
from app.services.tmdb import TMDBRateLimitError, TMDBService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["import"])


def to_naive_utc(dt: datetime | None) -> datetime | None:
    """Convert a datetime to naive UTC datetime for database storage."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def calculate_confidence(parsed_title: str, parsed_year: int | None,
                         tmdb_title: str, tmdb_year: int | None) -> float:
    """Calculate match confidence score (0.0 - 1.0).

    Uses title similarity (60% weight) and year match (40% weight).
    """
    score = 0.0

    # Title similarity (0.0 - 0.6)
    title_ratio = SequenceMatcher(
        None,
        parsed_title.lower(),
        tmdb_title.lower()
    ).ratio()
    score += title_ratio * 0.6

    # Year match (0.0 - 0.4)
    if parsed_year and tmdb_year:
        if parsed_year == tmdb_year:
            score += 0.4
        elif abs(parsed_year - tmdb_year) == 1:
            score += 0.2  # Off by one year, still likely correct

    return min(score, 1.0)


async def match_movies_with_tmdb(
    parsed_movies: list,
    user_id: UUID,
    db: DbSession,
) -> tuple[list[MatchedMovieItem], int]:
    """Match parsed movies against TMDB with rate limiting.

    Args:
        parsed_movies: List of ParsedMovie objects from CSV parser.
        user_id: Current user's ID for checking existing rankings.
        db: Database session.

    Returns:
        Tuple of (matched movies list, already_ranked count).
    """
    matched: list[MatchedMovieItem] = []
    already_ranked = 0

    # Get user's existing ranked movie TMDB IDs
    existing_result = await db.execute(
        select(Movie.tmdb_id)
        .join(Ranking, Ranking.movie_id == Movie.id)
        .where(Ranking.user_id == user_id)
    )
    existing_tmdb_ids = set(row[0] for row in existing_result.all())

    async with TMDBService() as service:
        for i, movie in enumerate(parsed_movies):
            try:
                # Rate limiting: delay every 35 requests
                if i > 0 and i % 35 == 0:
                    await asyncio.sleep(1.0)

                results = await service.search_movies(
                    query=movie.title,
                    year=movie.year,
                )

                if results:
                    best_match = results[0]
                    confidence = calculate_confidence(
                        movie.title, movie.year,
                        best_match.title, best_match.year
                    )

                    # Check if already ranked
                    if best_match.tmdb_id in existing_tmdb_ids:
                        already_ranked += 1
                        continue  # Skip already-ranked movies

                    matched.append(MatchedMovieItem(
                        parsed=ParsedMovieItem(
                            title=movie.title,
                            watch_date=movie.watch_date,
                            prime_image_url=movie.prime_image_url,
                        ),
                        tmdb_match=TMDBMatchResult(
                            tmdb_id=best_match.tmdb_id,
                            title=best_match.title,
                            year=best_match.year,
                            poster_url=best_match.poster_url,
                            overview=best_match.overview,
                        ),
                        confidence=confidence,
                        alternatives=[
                            TMDBMatchResult(
                                tmdb_id=r.tmdb_id,
                                title=r.title,
                                year=r.year,
                                poster_url=r.poster_url,
                                overview=r.overview,
                            )
                            for r in results[1:3]  # Up to 2 alternatives
                        ],
                        status="pending",
                    ))
                else:
                    # No TMDB match found
                    matched.append(MatchedMovieItem(
                        parsed=ParsedMovieItem(
                            title=movie.title,
                            watch_date=movie.watch_date,
                            prime_image_url=movie.prime_image_url,
                        ),
                        tmdb_match=None,
                        confidence=0.0,
                        alternatives=[],
                        status="pending",
                    ))

            except TMDBRateLimitError:
                # Wait and retry once
                logger.warning(f"Rate limited on movie {i}, waiting 2 seconds...")
                await asyncio.sleep(2.0)
                try:
                    results = await service.search_movies(query=movie.title)
                    if results:
                        best_match = results[0]
                        if best_match.tmdb_id not in existing_tmdb_ids:
                            matched.append(MatchedMovieItem(
                                parsed=ParsedMovieItem(
                                    title=movie.title,
                                    watch_date=movie.watch_date,
                                    prime_image_url=movie.prime_image_url,
                                ),
                                tmdb_match=TMDBMatchResult(
                                    tmdb_id=best_match.tmdb_id,
                                    title=best_match.title,
                                    year=best_match.year,
                                    poster_url=best_match.poster_url,
                                    overview=best_match.overview,
                                ),
                                confidence=calculate_confidence(
                                    movie.title, movie.year,
                                    best_match.title, best_match.year
                                ),
                                alternatives=[],
                                status="pending",
                            ))
                        else:
                            already_ranked += 1
                    else:
                        matched.append(MatchedMovieItem(
                            parsed=ParsedMovieItem(
                                title=movie.title,
                                watch_date=movie.watch_date,
                                prime_image_url=movie.prime_image_url,
                            ),
                            tmdb_match=None,
                            confidence=0.0,
                            alternatives=[],
                            status="pending",
                        ))
                except TMDBRateLimitError:
                    # Still rate limited, mark as unmatched
                    matched.append(MatchedMovieItem(
                        parsed=ParsedMovieItem(
                            title=movie.title,
                            watch_date=movie.watch_date,
                            prime_image_url=movie.prime_image_url,
                        ),
                        tmdb_match=None,
                        confidence=0.0,
                        alternatives=[],
                        status="pending",
                    ))

            except Exception as e:
                logger.error(f"Error matching movie '{movie.title}': {e}")
                matched.append(MatchedMovieItem(
                    parsed=ParsedMovieItem(
                        title=movie.title,
                        watch_date=movie.watch_date,
                        prime_image_url=movie.prime_image_url,
                    ),
                    tmdb_match=None,
                    confidence=0.0,
                    alternatives=[],
                    status="pending",
                ))

    return matched, already_ranked


@router.post(
    "/amazon-prime/upload/",
    response_model=ImportSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Amazon Prime CSV file",
    responses={
        201: {"description": "Import session created successfully"},
        400: {"description": "Invalid CSV file"},
        401: {"description": "Not authenticated"},
    },
)
async def upload_amazon_prime_csv(
    file: UploadFile,
    current_user: CurrentUser,
    db: DbSession,
) -> ImportSessionResponse:
    """Upload and parse an Amazon Prime Video watch history CSV file.

    Parses the CSV, matches movies against TMDB, and creates an import session
    for the user to review and add movies to their rankings.
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV file",
        )

    # Parse CSV
    parse_result = parse_amazon_prime_csv(file.file)

    if parse_result.total_entries == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file is empty or could not be parsed",
        )

    if parse_result.movies_found == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No movies found in CSV file (only TV shows?)",
        )

    # Match movies with TMDB
    matched_movies, already_ranked = await match_movies_with_tmdb(
        parse_result.movies,
        current_user.id,
        db,
    )

    # Create session
    session_id = import_session_store.create_session(
        user_id=str(current_user.id),
        movies=[m.model_dump() for m in matched_movies],
        total_entries=parse_result.total_entries,
        movies_found=parse_result.movies_found,
        tv_shows_filtered=parse_result.tv_shows_filtered,
        already_ranked=already_ranked,
    )

    return ImportSessionResponse(
        session_id=session_id,
        total_entries=parse_result.total_entries,
        movies_found=parse_result.movies_found,
        tv_shows_filtered=parse_result.tv_shows_filtered,
        already_ranked=already_ranked,
        ready_for_review=len(matched_movies),
        movies=matched_movies,
    )


@router.get(
    "/amazon-prime/session/{session_id}/",
    response_model=ImportSessionDetailResponse,
    summary="Get import session details",
    responses={
        200: {"description": "Session retrieved successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Session not found or expired"},
    },
)
async def get_import_session(
    session_id: str,
    current_user: CurrentUser,
) -> ImportSessionDetailResponse:
    """Get the current state of an import session."""
    session = import_session_store.get_session(session_id, str(current_user.id))

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import session not found or expired",
        )

    movies = [MatchedMovieItem(**m) for m in session.movies]
    pending_count = sum(1 for m in movies if m.status == "pending")

    return ImportSessionDetailResponse(
        session_id=session_id,
        current_index=session.current_index,
        total_movies=len(movies),
        added_count=session.added_count,
        skipped_count=session.skipped_count,
        remaining_count=pending_count,
        movies=movies,
    )


@router.post(
    "/amazon-prime/session/{session_id}/movie/{index}/add/",
    response_model=RankingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add movie from import session",
    responses={
        201: {"description": "Movie added to rankings"},
        400: {"description": "Movie has no TMDB match or already processed"},
        401: {"description": "Not authenticated"},
        404: {"description": "Session or movie not found"},
    },
)
async def add_import_movie(
    session_id: str,
    index: int,
    request: ImportMovieAddRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> Ranking:
    """Add a movie from the import session to user's rankings."""
    session = import_session_store.get_session(session_id, str(current_user.id))

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import session not found or expired",
        )

    if index < 0 or index >= len(session.movies):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie index out of range",
        )

    movie_data = MatchedMovieItem(**session.movies[index])

    if movie_data.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Movie has already been processed",
        )

    if movie_data.tmdb_match is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add movie without TMDB match",
        )

    # Get or create movie in database
    tmdb_id = movie_data.tmdb_match.tmdb_id
    result = await db.execute(select(Movie).where(Movie.tmdb_id == tmdb_id))
    movie = result.scalar_one_or_none()

    if movie is None:
        # Create new movie
        movie = Movie(
            tmdb_id=tmdb_id,
            title=movie_data.tmdb_match.title,
            year=movie_data.tmdb_match.year,
            poster_url=movie_data.tmdb_match.poster_url,
        )
        db.add(movie)
        await db.flush()
        await db.refresh(movie)

    # Determine rated_at: use request value, fall back to watch_date, then now
    rated_at = to_naive_utc(request.rated_at)
    if rated_at is None and movie_data.parsed.watch_date:
        rated_at = to_naive_utc(movie_data.parsed.watch_date)
    if rated_at is None:
        rated_at = datetime.utcnow()

    # Create ranking
    ranking = Ranking(
        user_id=current_user.id,
        movie_id=movie.id,
        rating=request.rating,
        rated_at=rated_at,
    )
    db.add(ranking)
    await db.flush()
    await db.refresh(ranking)

    # Update session state
    session.movies[index]["status"] = "added"
    session.added_count += 1
    session.current_index = index + 1

    return ranking


@router.post(
    "/amazon-prime/session/{session_id}/movie/{index}/skip/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Skip movie in import session",
    responses={
        204: {"description": "Movie skipped"},
        400: {"description": "Movie already processed"},
        401: {"description": "Not authenticated"},
        404: {"description": "Session or movie not found"},
    },
)
async def skip_import_movie(
    session_id: str,
    index: int,
    current_user: CurrentUser,
) -> None:
    """Skip a movie in the import session."""
    session = import_session_store.get_session(session_id, str(current_user.id))

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import session not found or expired",
        )

    if index < 0 or index >= len(session.movies):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie index out of range",
        )

    movie_data = MatchedMovieItem(**session.movies[index])

    if movie_data.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Movie has already been processed",
        )

    # Update session state
    session.movies[index]["status"] = "skipped"
    session.skipped_count += 1
    session.current_index = index + 1


@router.delete(
    "/amazon-prime/session/{session_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel import session",
    responses={
        204: {"description": "Session cancelled"},
        401: {"description": "Not authenticated"},
        404: {"description": "Session not found"},
    },
)
async def cancel_import_session(
    session_id: str,
    current_user: CurrentUser,
) -> None:
    """Cancel and delete an import session."""
    session = import_session_store.get_session(session_id, str(current_user.id))

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import session not found or expired",
        )

    import_session_store.delete_session(session_id)
```

### Register Router in main.py

Add to `/Users/stephen/Projects/movie-ranking/app/main.py`:

```python
from app.routers import import_amazon

# In router registration section:
app.include_router(import_amazon.router, prefix="/api/v1/import")
```

### Technical Decisions

- **Confidence calculation:** SequenceMatcher for title similarity (standard library, no new deps)
- **Rate limiting:** Delay every 35 requests, not per-request (batch efficiency)
- **Already-ranked filter:** Check at match time, not in session (cleaner data)
- **Movie creation:** Use get-or-create pattern for TMDB movies

---

## Acceptance Criteria

- [ ] POST /upload/ accepts multipart CSV file
- [ ] POST /upload/ validates .csv file extension
- [ ] POST /upload/ returns 400 for empty or invalid CSV
- [ ] POST /upload/ parses CSV and matches with TMDB
- [ ] POST /upload/ filters already-ranked movies
- [ ] POST /upload/ creates session and returns summary
- [ ] GET /session/{id}/ returns session state with progress
- [ ] GET /session/{id}/ returns 404 for expired/invalid session
- [ ] POST /movie/{index}/add/ creates movie if not exists
- [ ] POST /movie/{index}/add/ creates ranking with rating
- [ ] POST /movie/{index}/add/ uses watch_date as default rated_at
- [ ] POST /movie/{index}/add/ updates session state
- [ ] POST /movie/{index}/skip/ marks movie as skipped
- [ ] POST /movie/{index}/skip/ updates session state
- [ ] DELETE /session/{id}/ removes session
- [ ] All endpoints enforce user ownership
- [ ] All endpoints use trailing slashes
- [ ] Rate limiting prevents TMDB 429 errors

---

## Testing Requirements

- [ ] Integration test: Full upload-to-ranking flow
- [ ] Integration test: Session expiry handling
- [ ] Integration test: Already-ranked movie filtering
- [ ] Unit test: Confidence calculation with various inputs
- [ ] Unit test: Rate limiting delays (mock asyncio.sleep)

---

## Handoff Notes

### For Next Task (task-04)
- All API endpoints are now available
- Endpoints follow project conventions (trailing slashes, status codes)
- Response schemas match ImportSessionResponse, ImportSessionDetailResponse, etc.

### Artifacts Produced
- `/Users/stephen/Projects/movie-ranking/app/routers/import_amazon.py`
- Modified `/Users/stephen/Projects/movie-ranking/app/main.py`
