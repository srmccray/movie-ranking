# Refinement Notes: Amazon Prime Movie History Import

**Refined:** 2026-01-17
**FRD Location:** `.claude_docs/features/amazon-prime-import/frd.md`
**Tier:** MEDIUM

---

## Executive Summary

The FRD is well-structured and aligns with existing codebase patterns. Key refinements needed: (1) clarify session storage approach for single-server deployment, (2) document specific TMDB rate limiting implementation, (3) resolve open questions with recommended decisions, and (4) add file upload handling specifics for FastAPI.

---

## Codebase Alignment

### Verified Assumptions

| FRD Claim | Validation | Evidence |
|-----------|------------|----------|
| TMDB service exists for movie matching | Confirmed | `/Users/stephen/Projects/movie-ranking/app/services/tmdb.py` - `TMDBService.search_movies()` |
| Rankings API for creating rankings | Confirmed | `/Users/stephen/Projects/movie-ranking/app/routers/rankings.py` - `create_or_update_ranking()` |
| Movies API for creating movies | Confirmed | `/Users/stephen/Projects/movie-ranking/app/routers/movies.py` - `create_movie()` |
| Settings page exists for integration | Confirmed | `/Users/stephen/Projects/movie-ranking/frontend/src/pages/SettingsPage.tsx` |
| Modal component available | Confirmed | `/Users/stephen/Projects/movie-ranking/frontend/src/components/Modal.tsx` |
| StarRating component available | Confirmed | `/Users/stephen/Projects/movie-ranking/frontend/src/components/StarRating.tsx` |

### Corrections/Clarifications Needed

1. **File Upload Pattern**: FastAPI file uploads use `UploadFile` from `fastapi`, not standard form handling. The FRD should specify this.

2. **TMDB Rate Limiting**: The existing service already handles 429 responses with `TMDBRateLimitError`. The FRD should leverage this rather than implementing custom rate limiting.

3. **Session Storage**: The FRD mentions in-memory storage. For a single-server deployment this works, but the implementation should use a simple dict-based approach consistent with `oauth_state` pattern.

---

## Key Files

### Will Modify

| File | Changes |
|------|---------|
| `/Users/stephen/Projects/movie-ranking/frontend/src/pages/SettingsPage.tsx` | Add "Import Watch History" section |
| `/Users/stephen/Projects/movie-ranking/app/main.py` | Register new import router |

### Will Create

| File | Purpose |
|------|---------|
| `/Users/stephen/Projects/movie-ranking/app/routers/import_amazon.py` | Import endpoints for Amazon Prime CSV |
| `/Users/stephen/Projects/movie-ranking/app/services/csv_parser.py` | CSV parsing service |
| `/Users/stephen/Projects/movie-ranking/app/services/import_session.py` | Session storage management |
| `/Users/stephen/Projects/movie-ranking/app/schemas/import_amazon.py` | Request/response schemas for import |
| `/Users/stephen/Projects/movie-ranking/frontend/src/components/ImportWizard.tsx` | Multi-step import wizard |
| `/Users/stephen/Projects/movie-ranking/frontend/src/components/ImportFileUpload.tsx` | File upload step |
| `/Users/stephen/Projects/movie-ranking/frontend/src/components/ImportReview.tsx` | Movie review step |
| `/Users/stephen/Projects/movie-ranking/frontend/src/components/ImportComplete.tsx` | Completion summary |

### Reference (read-only patterns)

| File | Pattern to Follow |
|------|-------------------|
| `/Users/stephen/Projects/movie-ranking/app/services/tmdb.py` | Service class pattern, error handling, async context manager |
| `/Users/stephen/Projects/movie-ranking/app/routers/rankings.py` | Router pattern, trailing slashes, response models |
| `/Users/stephen/Projects/movie-ranking/app/routers/google_auth.py` | Session/state management pattern |
| `/Users/stephen/Projects/movie-ranking/frontend/src/pages/SettingsPage.tsx` | Settings section structure, status handling |
| `/Users/stephen/Projects/movie-ranking/frontend/src/components/Modal.tsx` | Modal accessibility pattern |
| `/Users/stephen/Projects/movie-ranking/frontend/src/components/MovieCard.tsx` | Movie display pattern, poster handling |

---

## Technical Decisions

### Open Questions Resolved

| Question | Decision | Rationale |
|----------|----------|-----------|
| Support other streaming services? | **No** - Amazon-specific for now | Keep scope focused. Router path `/api/v1/import/amazon-prime/` allows future expansion without breaking changes. |
| What if user starts new import while one is in progress? | **Replace** the existing session | Simpler UX; user intent is to start fresh. Clear old session when new upload received. |
| Persist unmatched movies? | **No** - show in completion summary only | Adds complexity; users can manually search for unmatched movies using existing search. |
| Use Prime watch date as `rated_at`? | **Yes** - default to watch date | More meaningful for users; they watched it on that date. Allow override in review step. |
| Bulk add option? | **Defer** to v2 | Start with one-by-one review for accuracy. Can add "Add all with 3+ confidence" later. |

### Session Storage Approach

**Recommended:** In-memory dict with TTL, similar to OAuth state pattern.

```python
# app/services/import_session.py
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional
from uuid import uuid4

class ImportSessionStore:
    """In-memory store for import sessions with automatic cleanup."""

    SESSION_TTL_MINUTES = 30
    MAX_MOVIES_PER_SESSION = 500

    def __init__(self):
        self._sessions: Dict[str, ImportSession] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    async def create_session(self, user_id: str, movies: list) -> str:
        session_id = str(uuid4())
        self._sessions[session_id] = ImportSession(
            user_id=user_id,
            movies=movies[:self.MAX_MOVIES_PER_SESSION],
            created_at=datetime.utcnow(),
            current_index=0,
        )
        return session_id

    def get_session(self, session_id: str, user_id: str) -> Optional[ImportSession]:
        session = self._sessions.get(session_id)
        if session and session.user_id == user_id:
            if datetime.utcnow() - session.created_at < timedelta(minutes=self.SESSION_TTL_MINUTES):
                return session
            else:
                del self._sessions[session_id]
        return None
```

**Why this approach:**
- Matches existing OAuth state pattern in codebase
- Simple for single-server deployment
- No database migration needed
- Session data is temporary by design
- Automatic cleanup prevents memory leaks

### TMDB Rate Limiting Strategy

**Recommended:** Batch processing with existing error handling.

```python
async def match_movies_with_tmdb(movies: list[ParsedMovie]) -> list[MatchedMovie]:
    """Match parsed movies against TMDB with rate limiting."""
    matched = []

    async with TMDBService() as service:
        for i, movie in enumerate(movies):
            try:
                # TMDB free tier: 40 requests/10 seconds
                # Add small delay every 35 requests to stay under limit
                if i > 0 and i % 35 == 0:
                    await asyncio.sleep(1.0)

                results = await service.search_movies(
                    query=movie.title,
                    year=movie.year,
                )

                if results:
                    matched.append(MatchedMovie(
                        parsed=movie,
                        tmdb_match=results[0],
                        confidence=calculate_confidence(movie, results[0]),
                        alternatives=results[1:3] if len(results) > 1 else [],
                    ))
                else:
                    matched.append(MatchedMovie(
                        parsed=movie,
                        tmdb_match=None,
                        confidence=0,
                        alternatives=[],
                    ))

            except TMDBRateLimitError:
                # Wait and retry once
                await asyncio.sleep(2.0)
                try:
                    results = await service.search_movies(query=movie.title)
                    # ... handle result
                except TMDBRateLimitError:
                    # Mark as unmatched, continue with others
                    matched.append(MatchedMovie(parsed=movie, tmdb_match=None, confidence=0))

    return matched
```

### Matching Confidence Calculation

```python
def calculate_confidence(parsed: ParsedMovie, tmdb: TMDBMovieResult) -> float:
    """Calculate match confidence score (0.0 - 1.0)."""
    score = 0.0

    # Title similarity (0.0 - 0.6)
    title_ratio = SequenceMatcher(None,
        parsed.title.lower(),
        tmdb.title.lower()
    ).ratio()
    score += title_ratio * 0.6

    # Year match (0.0 - 0.4)
    if parsed.year and tmdb.year:
        if parsed.year == tmdb.year:
            score += 0.4
        elif abs(parsed.year - tmdb.year) == 1:
            score += 0.2  # Off by one year, still likely correct

    return min(score, 1.0)
```

**Threshold:** 0.7+ = high confidence (auto-select), <0.5 = needs review flag

---

## API Design Refinements

### Endpoint Corrections

All endpoints follow project trailing slash convention:

```
POST /api/v1/import/amazon-prime/upload/
  Content-Type: multipart/form-data
  Body: file (CSV file)
  Response: ImportSessionResponse (201 Created)

GET /api/v1/import/amazon-prime/session/{session_id}/
  Response: ImportSessionDetailResponse

POST /api/v1/import/amazon-prime/session/{session_id}/movie/{index}/add/
  Body: { "rating": 1-5, "rated_at": "ISO8601" (optional) }
  Response: RankingResponse (201 Created)

POST /api/v1/import/amazon-prime/session/{session_id}/movie/{index}/skip/
  Response: 204 No Content

DELETE /api/v1/import/amazon-prime/session/{session_id}/
  Response: 204 No Content
```

### Schema Definitions

```python
# app/schemas/import_amazon.py

class ParsedMovieItem(BaseModel):
    """A movie parsed from the CSV file."""
    title: str
    watch_date: datetime | None
    prime_image_url: str | None

class MatchedMovieItem(BaseModel):
    """A parsed movie with TMDB match results."""
    parsed: ParsedMovieItem
    tmdb_match: TMDBSearchResult | None
    confidence: float = Field(ge=0.0, le=1.0)
    alternatives: list[TMDBSearchResult] = []
    status: Literal["pending", "added", "skipped"] = "pending"

class ImportSessionResponse(BaseModel):
    """Response after uploading CSV file."""
    session_id: str
    total_entries: int
    movies_found: int
    tv_shows_filtered: int
    already_ranked: int
    ready_for_review: int
    movies: list[MatchedMovieItem]

class ImportSessionDetailResponse(BaseModel):
    """Current session state."""
    session_id: str
    current_index: int
    total_movies: int
    added_count: int
    skipped_count: int
    remaining_count: int
    movies: list[MatchedMovieItem]

class ImportMovieAddRequest(BaseModel):
    """Request to add a movie from import session."""
    rating: int = Field(ge=1, le=5)
    rated_at: datetime | None = None  # Defaults to watch_date from CSV

class ImportCompletionResponse(BaseModel):
    """Summary after completing import."""
    movies_added: int
    movies_skipped: int
    unmatched_titles: list[str]
```

---

## Frontend Integration

### SettingsPage Section

Add to SettingsPage.tsx after "Connected Accounts" section:

```tsx
{/* Import Watch History Section */}
<section className="settings-section">
  <h2 className="settings-section-title">Import Watch History</h2>
  <div className="settings-card">
    <div className="settings-row settings-row-action">
      <div className="settings-row-info">
        <div className="settings-label">Amazon Prime Video</div>
        <div className="settings-description">
          Import your watch history from Amazon Prime Video using a CSV export.
        </div>
      </div>
      <Button onClick={() => setShowImportWizard(true)}>
        Import
      </Button>
    </div>
  </div>
</section>

{/* Import Wizard Modal */}
{showImportWizard && (
  <ImportWizard
    onClose={() => setShowImportWizard(false)}
    onComplete={handleImportComplete}
  />
)}
```

### Component State Flow

```
ImportWizard (parent container)
  |-- step: 'upload' | 'review' | 'complete'
  |-- sessionId: string | null
  |
  |-- ImportFileUpload (step === 'upload')
  |     |-- onUploadComplete(sessionId, summary)
  |
  |-- ImportReview (step === 'review')
  |     |-- movies: MatchedMovieItem[]
  |     |-- currentIndex: number
  |     |-- onAdd(rating, ratedAt?)
  |     |-- onSkip()
  |     |-- onSelectAlternative(altIndex)
  |
  |-- ImportComplete (step === 'complete')
        |-- summary: { added, skipped, unmatched[] }
        |-- onDone()
```

### API Client Methods

```typescript
// frontend/src/api/client.ts additions

async uploadAmazonPrimeCSV(file: File): Promise<ImportSessionResponse> {
  const formData = new FormData();
  formData.append('file', file);

  return this.request<ImportSessionResponse>('/import/amazon-prime/upload/', {
    method: 'POST',
    body: formData,
    // Note: Don't set Content-Type, browser will set multipart/form-data with boundary
  });
}

async getImportSession(sessionId: string): Promise<ImportSessionDetailResponse> {
  return this.request<ImportSessionDetailResponse>(
    `/import/amazon-prime/session/${sessionId}/`
  );
}

async addImportMovie(
  sessionId: string,
  movieIndex: number,
  rating: number,
  ratedAt?: string
): Promise<Ranking> {
  return this.request<Ranking>(
    `/import/amazon-prime/session/${sessionId}/movie/${movieIndex}/add/`,
    {
      method: 'POST',
      body: JSON.stringify({ rating, rated_at: ratedAt }),
    }
  );
}

async skipImportMovie(sessionId: string, movieIndex: number): Promise<void> {
  await this.request<void>(
    `/import/amazon-prime/session/${sessionId}/movie/${movieIndex}/skip/`,
    { method: 'POST' }
  );
}

async cancelImportSession(sessionId: string): Promise<void> {
  await this.request<void>(
    `/import/amazon-prime/session/${sessionId}/`,
    { method: 'DELETE' }
  );
}
```

---

## Blockers / Concerns

### None Blocking

All required dependencies exist in the codebase. No external dependencies needed beyond what's already installed.

### Minor Concerns

1. **Large CSV Files**: 500 movie limit is reasonable, but frontend should show clear feedback if file is truncated.

2. **Session Cleanup**: In-memory sessions will be lost on server restart. For MVP this is acceptable - users can re-upload.

3. **TMDB Match Accuracy**: Some Amazon titles may be localized or abbreviated. Confidence threshold should be tested with real data.

---

## Ready for Implementation

- [x] FRD assumptions validated
- [x] Open questions resolved with recommendations
- [x] No major blockers identified
- [x] API design follows existing patterns
- [x] Frontend integration points identified
- [x] Session storage approach defined
- [x] Rate limiting strategy defined

---

## Next Agent to Invoke

**Agent:** `frd-task-breakdown`

**Context to provide:**
- Feature slug: `amazon-prime-import`
- Tier: MEDIUM
- Refinement summary: In-memory session storage validated, TMDB matching uses existing service with batch delays, all open questions resolved with concrete decisions
- Key files: `/Users/stephen/Projects/movie-ranking/app/routers/import_amazon.py` (new), `/Users/stephen/Projects/movie-ranking/frontend/src/components/ImportWizard.tsx` (new), `/Users/stephen/Projects/movie-ranking/frontend/src/pages/SettingsPage.tsx` (modify)

**After that agent completes:**
Task breakdown document with implementation steps, ready for backend and frontend implementation agents.
