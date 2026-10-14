---
id: '0001'
title: Amazon Prime Watch History Import
status: Shipped
created: 2026-10-13
target_persona: Casey (The Movie Enthusiast)
component: import
---

# PRD-0001 — Amazon Prime Watch History Import

## Who this is for

- **Casey (The Movie Enthusiast)**: Wants to quickly populate rankings with movies already watched on Amazon Prime Video.

## What the person cannot do today

- Users must remember which movies they watched on Prime, search for each individually, and add/rate each one manually.
- This tedium discourages adoption, especially for users with long Prime viewing histories.

## What good looks like

1. **CSV Upload**: Upload an Amazon Prime watch-history CSV from the Settings page.
2. **Parsing & Filtering**: TV series are filtered out; already-ranked movies are skipped.
3. **TMDB Matching**: Movies are matched with a confidence score (title similarity 0.6 + year 0.4) and up to 2 alternatives, with rate limiting (1s delay per 35 requests).
4. **Review Workflow**: One-by-one add (with 1-5 rating, rated_at defaulting to watch date) or skip, with progress indicator and completion summary.
5. **Session Storage**: In-memory import session, 30-minute TTL, max 500 movies, new upload replaces an existing session.

## What this does not do

- Other streaming services (Netflix, etc.) — router path `/api/v1/import/amazon-prime/` leaves room for later.
- Persisting unmatched movies for later matching.
- Bulk-add of high-confidence matches (deferred to v2).
- Persistence of sessions across server restarts.
- New database tables.

## Checkable Outcomes

1. User can upload a CSV file from Settings page
2. System correctly parses Amazon Prime CSV format
3. TV shows are filtered out, only movies are imported
4. Movies are matched against TMDB with reasonable accuracy
5. User can review movies one-by-one with add/skip options
6. User can set rating when adding a movie
7. Already-ranked movies are identified and skipped
8. User sees import summary upon completion
9. Session data is cleaned up after completion or timeout
10. Invalid uploads and expired sessions return 4xx responses whose error message is displayed in the import wizard
11. API endpoints use trailing slashes per project convention

## Linked User Stories

- `US-0001`

## Implementing Backlog Tasks

- `TASK-0002`
- `TASK-0003`
- `TASK-0004`
- `TASK-0005`
- `TASK-0006`
- `TASK-0007`

## Shipped Evidence

- Shipped in commit `0941314` (2026-01-17): `app/routers/import_amazon.py`, `app/services/csv_parser.py`, `app/services/import_session.py`, `frontend/src/components/Import*.tsx`, `tests/test_import_amazon.py`.

## Legacy Specification

_Migrated verbatim (headings demoted) from the legacy `.claude_docs/` tree on 2026-10-13._

### Source: `.claude_docs/features/amazon-prime-import/frd.md`

### FRD: Amazon Prime Movie History Import

**Created:** 2026-01-17
**Refined:** 2026-01-17
**Tier:** MEDIUM
**Triage Scores:** Complexity 6.5/10, Risk 4.3/10
**Status:** Refined

#### Problem Statement

Users who have been watching movies on Amazon Prime Video have no way to bring their viewing history into the Movie Ranking app. This creates friction for new users who want to quickly populate their rankings with movies they've already watched, rather than manually searching for and adding each movie one by one.

Currently, users must:
1. Remember which movies they've watched on Prime
2. Search for each movie individually in the app
3. Add and rate each movie manually

This manual process is tedious and discourages users from fully adopting the app, especially those with extensive Prime viewing histories.

#### Proposed Solution

##### Overview

Implement a multi-step import workflow that allows users to upload a CSV export of their Amazon Prime Video watch history, match those movies against TMDB, and selectively add movies to their rankings with ratings.

##### Key Components

1. **CSV File Upload**: A file input in the Settings page that accepts CSV files exported from Amazon Prime Video using third-party tools.

2. **CSV Parser**: Backend service to parse the Amazon Prime CSV format and extract movie data (filtering out TV series).

3. **TMDB Matcher**: Service that uses the existing TMDB integration to find matching movies by title and year.

4. **Import Session**: Temporary in-memory storage of parsed/matched movies for the duration of the import workflow.

5. **Review Workflow**: Step-by-step UI where users review each matched movie and decide to add (with rating) or skip.

##### User Experience

**Entry Point:**
- Settings page displays a new "Import Watch History" section
- User clicks "Import from Amazon Prime" button

**Upload Flow:**
1. User selects their CSV file
2. System parses the file and displays a summary:
   - Total entries found
   - Movies identified (vs. TV shows filtered out)
   - Already-ranked movies (will be skipped)
   - Movies ready for review

**Review Flow:**
1. User is presented with one movie at a time
2. Each movie card shows:
   - Movie poster and details from TMDB
   - Original Prime watch date
   - Match confidence indicator (if multiple matches found)
3. User can:
   - Rate the movie (1-5 stars) and add it
   - Skip this movie
   - Mark as "Not this movie" and see alternatives (if available)
4. Progress indicator shows position in queue

**Completion:**
- Summary screen shows:
  - Movies added
  - Movies skipped
  - Any unmatched titles (with manual search option)

#### Technical Approach

##### Backend Changes

###### New Router: `/api/v1/import/`

All endpoints use trailing slashes per project convention.

```
POST /api/v1/import/amazon-prime/upload/
  - Content-Type: multipart/form-data
  - Body: file (CSV file upload via FastAPI UploadFile)
  - Returns: ImportSessionResponse (201 Created)
    {
      session_id: string,
      total_entries: int,
      movies_found: int,
      tv_shows_filtered: int,
      already_ranked: int,
      ready_for_review: int,
      movies: MatchedMovieItem[]
    }

GET /api/v1/import/amazon-prime/session/{session_id}/
  - Returns: ImportSessionDetailResponse (200 OK)
    {
      session_id: string,
      current_index: int,
      total_movies: int,
      added_count: int,
      skipped_count: int,
      remaining_count: int,
      movies: MatchedMovieItem[]
    }

POST /api/v1/import/amazon-prime/session/{session_id}/movie/{index}/add/
  - Body: { "rating": 1-5, "rated_at": "ISO8601" (optional, defaults to watch_date) }
  - Returns: RankingResponse (201 Created)

POST /api/v1/import/amazon-prime/session/{session_id}/movie/{index}/skip/
  - Returns: 204 No Content

DELETE /api/v1/import/amazon-prime/session/{session_id}/
  - Returns: 204 No Content
```

###### CSV Parsing Service

Parse Amazon Prime CSV format:
- **Date Watched**: Parse to datetime (format: varies by locale)
- **Type**: Filter for "Movie" only (skip "Series")
- **Title**: Movie title for TMDB search
- **Image URL**: Fallback poster if TMDB match fails

Expected CSV columns:
```
Date Watched,Type,Title,Episode Title,Global Title Identifier,Episode Global Title Identifier,Path,Episode Path,Image URL
```

###### TMDB Matching Strategy

For each movie title:
1. Search TMDB with exact title using existing `TMDBService.search_movies()`
2. If watch date available, extract year and include in search
3. Score matches using confidence calculation:
   - Title similarity via SequenceMatcher (0.0 - 0.6 weight)
   - Year match: exact = 0.4, off-by-one = 0.2
4. Return top match with confidence score (0.0 - 1.0)
5. Confidence thresholds:
   - >= 0.7: High confidence, auto-selected as best match
   - < 0.5: Low confidence, flagged as "needs review"
6. Include up to 2 alternatives for user selection

**Rate Limiting:** Batch TMDB lookups with 1-second delay every 35 requests to stay under TMDB free tier limit (40 req/10s). If TMDBRateLimitError occurs, wait 2 seconds and retry once.

###### Session Storage

Use in-memory storage via `ImportSessionStore` class (similar to OAuth state pattern):
- Sessions expire after 30 minutes (TTL)
- Maximum 500 movies per session (excess movies truncated with user notification)
- Session contains:
  - `user_id`: For authorization (only owner can access session)
  - `movies`: List of MatchedMovieItem with match status
  - `current_index`: Current position in review
  - `created_at`: For TTL calculation
  - Added/skipped counts

**Note:** Sessions are lost on server restart. This is acceptable for MVP - users can re-upload if needed.

##### Frontend Changes

###### New Import Components

1. **ImportWizard**: Multi-step wizard container
2. **FileUploadStep**: CSV file selection and upload
3. **ReviewStep**: Movie-by-movie review interface
4. **CompletionStep**: Summary and next actions

###### State Management

Use local component state for the import wizard:
- Current step (upload, review, complete)
- Session ID from backend
- Current movie index
- Local cache of session data

###### Settings Page Integration

Add new section to SettingsPage:
```tsx
<section className="settings-section">
  <h2 className="settings-section-title">Import Watch History</h2>
  <div className="settings-card">
    <div className="settings-row settings-row-action">
      <div className="settings-row-info">
        <div className="settings-label">Amazon Prime Video</div>
        <div className="settings-description">
          Import your watch history from Amazon Prime Video
        </div>
      </div>
      <Button onClick={handleOpenImport}>Import</Button>
    </div>
  </div>
</section>
```

##### Data Model

No new database tables required. Import sessions are temporary and in-memory. Movies and rankings use existing tables.

#### Implementation Notes

##### Dependencies

- Existing TMDB service for movie matching
- Existing rankings API for creating new rankings
- Existing movies API for creating new movies (if not exists)

##### Integration Points

- **TMDBService**: Leverage existing `search_movies()` method
- **Rankings Router**: Use existing `create_or_update_ranking()` for adding movies
- **Movies Router**: Use existing `get_or_create_movie()` pattern

##### Feature Flags

No feature flag needed for initial release. This is additive functionality in Settings.

##### Rate Limiting Considerations

- TMDB API has rate limits (40 requests/10 seconds for free tier)
- Implementation: 1-second delay every 35 requests during batch matching
- Leverage existing `TMDBRateLimitError` handling in `TMDBService`
- Show progress indicator during matching phase (e.g., "Matching movie 15 of 47...")
- If rate limit hit, wait 2 seconds and retry once before marking as unmatched

#### Testing Strategy

- **Unit tests:** CSV parser with various date formats and edge cases
- **Unit tests:** TMDB matching logic with mock responses
- **Integration tests:** Full upload-to-ranking flow
- **Manual testing:**
  - File with mixed movies and TV shows
  - File with movies already in user's rankings
  - File with movies that have no TMDB match
  - Large file (500+ entries)
  - Malformed CSV handling

#### Rollback Plan

1. Remove import section from Settings page
2. Remove import router from FastAPI app
3. No database changes to revert

#### Acceptance Criteria

- [ ] User can upload a CSV file from Settings page
- [ ] System correctly parses Amazon Prime CSV format
- [ ] TV shows are filtered out, only movies are imported
- [ ] Movies are matched against TMDB with reasonable accuracy
- [ ] User can review movies one-by-one with add/skip options
- [ ] User can set rating when adding a movie
- [ ] Already-ranked movies are identified and skipped
- [ ] User sees import summary upon completion
- [ ] Session data is cleaned up after completion or timeout
- [ ] Errors are handled gracefully with user-friendly messages
- [ ] API endpoints use trailing slashes per project convention

#### Open Questions (Resolved)

- [x] **Should we support other streaming service exports (Netflix, etc.) in the future?**
  - **Decision:** No, Amazon-specific for now. Router path `/api/v1/import/amazon-prime/` allows future expansion without breaking changes.
  - **Rationale:** Keep scope focused for MEDIUM tier feature.

- [x] **What should happen if a user starts a new import while one is in progress?**
  - **Decision:** Replace the existing session.
  - **Rationale:** Simpler UX; user intent is to start fresh. Clear old session when new upload received.

- [x] **Should we persist unmatched movies for later manual matching?**
  - **Decision:** No, show in completion summary only.
  - **Rationale:** Adds complexity; users can manually search for unmatched movies using existing search feature.

- [x] **Use Prime watch date as `rated_at` or import timestamp?**
  - **Decision:** Default to watch date from CSV.
  - **Rationale:** More meaningful for users - they watched it on that date. Allow override in review step if user wants different date.

- [x] **Bulk add option for trusted matches?**
  - **Decision:** Defer to v2.
  - **Rationale:** Start with one-by-one review for accuracy. Can add "Add all with X+ confidence" later based on user feedback.

---

#### Appendix

##### Amazon Prime CSV Format

The CSV export from third-party tools (e.g., Watch History Exporter) includes:

| Column | Description | Example |
|--------|-------------|---------|
| Date Watched | Watch timestamp | `2024-01-15` or `01/15/2024` |
| Type | Content type | `Movie` or `Series` |
| Title | Movie/show title | `The Dark Knight` |
| Episode Title | Episode name (blank for movies) | |
| Global Title Identifier | Amazon's internal ID | `amzn1.dv.gti.xyz123` |
| Episode Global Title Identifier | Episode ID | |
| Path | URL path to content | `/detail/B001...` |
| Episode Path | Episode URL path | |
| Image URL | Poster/thumbnail URL | `https://...jpg` |

##### References

- [Watch History Exporter for Amazon Prime Video (GitHub)](https://github.com/twocaretcat/watch-history-exporter-for-amazon-prime-video)
- [Prime Video History to CSV (Python)](https://github.com/gitzain/prime-video-history-to-csv)
- [Export script (JavaScript Gist)](https://gist.github.com/jerboa88/06cf269b9192802e2689d3850b79164c)

### Source: `.claude_docs/features/amazon-prime-import/refinement.md`

### Refinement Notes: Amazon Prime Movie History Import

**Refined:** 2026-01-17
**FRD Location:** `.claude_docs/features/amazon-prime-import/frd.md`
**Tier:** MEDIUM

---

#### Executive Summary

The FRD is well-structured and aligns with existing codebase patterns. Key refinements needed: (1) clarify session storage approach for single-server deployment, (2) document specific TMDB rate limiting implementation, (3) resolve open questions with recommended decisions, and (4) add file upload handling specifics for FastAPI.

---

#### Codebase Alignment

##### Verified Assumptions

| FRD Claim | Validation | Evidence |
|-----------|------------|----------|
| TMDB service exists for movie matching | Confirmed | `/Users/stephen/Projects/movie-ranking/app/services/tmdb.py` - `TMDBService.search_movies()` |
| Rankings API for creating rankings | Confirmed | `/Users/stephen/Projects/movie-ranking/app/routers/rankings.py` - `create_or_update_ranking()` |
| Movies API for creating movies | Confirmed | `/Users/stephen/Projects/movie-ranking/app/routers/movies.py` - `create_movie()` |
| Settings page exists for integration | Confirmed | `/Users/stephen/Projects/movie-ranking/frontend/src/pages/SettingsPage.tsx` |
| Modal component available | Confirmed | `/Users/stephen/Projects/movie-ranking/frontend/src/components/Modal.tsx` |
| StarRating component available | Confirmed | `/Users/stephen/Projects/movie-ranking/frontend/src/components/StarRating.tsx` |

##### Corrections/Clarifications Needed

1. **File Upload Pattern**: FastAPI file uploads use `UploadFile` from `fastapi`, not standard form handling. The FRD should specify this.

2. **TMDB Rate Limiting**: The existing service already handles 429 responses with `TMDBRateLimitError`. The FRD should leverage this rather than implementing custom rate limiting.

3. **Session Storage**: The FRD mentions in-memory storage. For a single-server deployment this works, but the implementation should use a simple dict-based approach consistent with `oauth_state` pattern.

---

#### Key Files

##### Will Modify

| File | Changes |
|------|---------|
| `/Users/stephen/Projects/movie-ranking/frontend/src/pages/SettingsPage.tsx` | Add "Import Watch History" section |
| `/Users/stephen/Projects/movie-ranking/app/main.py` | Register new import router |

##### Will Create

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

##### Reference (read-only patterns)

| File | Pattern to Follow |
|------|-------------------|
| `/Users/stephen/Projects/movie-ranking/app/services/tmdb.py` | Service class pattern, error handling, async context manager |
| `/Users/stephen/Projects/movie-ranking/app/routers/rankings.py` | Router pattern, trailing slashes, response models |
| `/Users/stephen/Projects/movie-ranking/app/routers/google_auth.py` | Session/state management pattern |
| `/Users/stephen/Projects/movie-ranking/frontend/src/pages/SettingsPage.tsx` | Settings section structure, status handling |
| `/Users/stephen/Projects/movie-ranking/frontend/src/components/Modal.tsx` | Modal accessibility pattern |
| `/Users/stephen/Projects/movie-ranking/frontend/src/components/MovieCard.tsx` | Movie display pattern, poster handling |

---

#### Technical Decisions

##### Open Questions Resolved

| Question | Decision | Rationale |
|----------|----------|-----------|
| Support other streaming services? | **No** - Amazon-specific for now | Keep scope focused. Router path `/api/v1/import/amazon-prime/` allows future expansion without breaking changes. |
| What if user starts new import while one is in progress? | **Replace** the existing session | Simpler UX; user intent is to start fresh. Clear old session when new upload received. |
| Persist unmatched movies? | **No** - show in completion summary only | Adds complexity; users can manually search for unmatched movies using existing search. |
| Use Prime watch date as `rated_at`? | **Yes** - default to watch date | More meaningful for users; they watched it on that date. Allow override in review step. |
| Bulk add option? | **Defer** to v2 | Start with one-by-one review for accuracy. Can add "Add all with 3+ confidence" later. |

##### Session Storage Approach

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

##### TMDB Rate Limiting Strategy

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

##### Matching Confidence Calculation

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

#### API Design Refinements

##### Endpoint Corrections

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

##### Schema Definitions

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

#### Frontend Integration

##### SettingsPage Section

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

##### Component State Flow

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

##### API Client Methods

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

#### Blockers / Concerns

##### None Blocking

All required dependencies exist in the codebase. No external dependencies needed beyond what's already installed.

##### Minor Concerns

1. **Large CSV Files**: 500 movie limit is reasonable, but frontend should show clear feedback if file is truncated.

2. **Session Cleanup**: In-memory sessions will be lost on server restart. For MVP this is acceptable - users can re-upload.

3. **TMDB Match Accuracy**: Some Amazon titles may be localized or abbreviated. Confidence threshold should be tested with real data.

---

#### Ready for Implementation

- [x] FRD assumptions validated
- [x] Open questions resolved with recommendations
- [x] No major blockers identified
- [x] API design follows existing patterns
- [x] Frontend integration points identified
- [x] Session storage approach defined
- [x] Rate limiting strategy defined

---

#### Next Agent to Invoke

**Agent:** `frd-task-breakdown`

**Context to provide:**
- Feature slug: `amazon-prime-import`
- Tier: MEDIUM
- Refinement summary: In-memory session storage validated, TMDB matching uses existing service with batch delays, all open questions resolved with concrete decisions
- Key files: `/Users/stephen/Projects/movie-ranking/app/routers/import_amazon.py` (new), `/Users/stephen/Projects/movie-ranking/frontend/src/components/ImportWizard.tsx` (new), `/Users/stephen/Projects/movie-ranking/frontend/src/pages/SettingsPage.tsx` (modify)

**After that agent completes:**
Task breakdown document with implementation steps, ready for backend and frontend implementation agents.

## Legacy Task Breakdown Index

_Migrated verbatim (headings demoted) from the legacy `.claude_docs/` tree on 2026-10-13._

### Source: `.claude_docs/tasks/amazon-prime-import/_index.md`

### Task Breakdown: Amazon Prime Movie History Import

**FRD:** `.claude_docs/features/amazon-prime-import/frd.md`
**Refinement:** `.claude_docs/features/amazon-prime-import/refinement.md`
**Created:** 2026-01-17
**Status:** Complete (verified against code on 2026-10-13)

---

#### Summary

Enable users to upload a CSV export of their Amazon Prime Video watch history, automatically match movies against TMDB, and selectively add them to their rankings through a step-by-step review workflow.

**Total Tasks:** 6
**Estimated Complexity:** Medium (6.5/10)

---

#### Task Overview

| # | Task | Agent | Status | Blocked By |
|---|------|-------|--------|------------|
| 01 | Backend Schemas and Session Storage | backend-implementation | Not Started | - |
| 02 | CSV Parser Service | backend-implementation | Not Started | 01 |
| 03 | Import Router and Endpoints | backend-implementation | Not Started | 01, 02 |
| 04 | Frontend API Client and Types | frontend-implementation | Not Started | 03 |
| 05 | Import Wizard Components | frontend-implementation | Not Started | 04 |
| 06 | Backend Integration Tests | test-coverage | Not Started | 03 |

**Status Legend:**
- Not Started
- In Progress
- Complete
- Blocked
- Cancelled

---

#### Dependency Graph

```
task-01 (Backend Schemas & Session Storage)
    |
    +---> task-02 (CSV Parser Service)
    |         |
    |         +---> task-03 (Import Router & Endpoints)
    |                   |
    |                   +---> task-04 (Frontend API Client & Types)
    |                   |         |
    |                   |         +---> task-05 (Import Wizard Components)
    |                   |
    |                   +---> task-06 (Backend Integration Tests)
```

---

#### Critical Path

1. task-01 -> task-02 -> task-03 -> task-04 -> task-05 (longest path to user-visible feature)

---

#### Parallel Opportunities

- task-04 (Frontend API Client) and task-06 (Backend Tests) can run in parallel after task-03 completes
- Frontend scaffolding (types, basic component structure) could begin while backend work is in progress, but full implementation requires API endpoints

---

#### Lateral Moves (Prerequisites)

None required. All dependencies exist in the codebase:
- TMDBService for movie matching
- Rankings router for creating rankings
- Movies router for creating movies
- SettingsPage for integration point
- Modal component for wizard container

---

#### Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Session Storage | In-memory dict with TTL | Matches existing OAuth state pattern, simple for single-server deployment |
| TMDB Rate Limiting | 1-second delay every 35 requests | Stay under free tier limit (40 req/10s), leverage existing error handling |
| Match Confidence | Title similarity (0.6) + Year match (0.4) | Balances accuracy with simplicity |
| New import while active | Replace existing session | Simpler UX; user intent is to start fresh |
| Watch date usage | Default rated_at to CSV watch date | More meaningful for users |

---

#### Files to Create

| File | Task | Purpose |
|------|------|---------|
| `/Users/stephen/Projects/movie-ranking/app/schemas/import_amazon.py` | 01 | Request/response schemas for import |
| `/Users/stephen/Projects/movie-ranking/app/services/import_session.py` | 01 | Session storage management |
| `/Users/stephen/Projects/movie-ranking/app/services/csv_parser.py` | 02 | CSV parsing service |
| `/Users/stephen/Projects/movie-ranking/app/routers/import_amazon.py` | 03 | Import endpoints |
| `/Users/stephen/Projects/movie-ranking/frontend/src/components/ImportWizard.tsx` | 05 | Multi-step wizard container |
| `/Users/stephen/Projects/movie-ranking/frontend/src/components/ImportFileUpload.tsx` | 05 | File upload step |
| `/Users/stephen/Projects/movie-ranking/frontend/src/components/ImportReview.tsx` | 05 | Movie review step |
| `/Users/stephen/Projects/movie-ranking/frontend/src/components/ImportComplete.tsx` | 05 | Completion summary |
| `/Users/stephen/Projects/movie-ranking/tests/test_import_amazon.py` | 06 | Integration tests |

#### Files to Modify

| File | Task | Changes |
|------|------|---------|
| `/Users/stephen/Projects/movie-ranking/app/main.py` | 03 | Register import router |
| `/Users/stephen/Projects/movie-ranking/frontend/src/api/client.ts` | 04 | Add import API methods |
| `/Users/stephen/Projects/movie-ranking/frontend/src/types/index.ts` | 04 | Add import types |
| `/Users/stephen/Projects/movie-ranking/frontend/src/components/index.ts` | 05 | Export new components |
| `/Users/stephen/Projects/movie-ranking/frontend/src/pages/SettingsPage.tsx` | 05 | Add Import section |

---

#### Progress Log

| Date | Task | Update |
|------|------|--------|
| 2026-01-17 | - | Task breakdown created |
