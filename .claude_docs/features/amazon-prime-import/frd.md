# FRD: Amazon Prime Movie History Import

**Created:** 2026-01-17
**Refined:** 2026-01-17
**Tier:** MEDIUM
**Triage Scores:** Complexity 6.5/10, Risk 4.3/10
**Status:** Refined

## Problem Statement

Users who have been watching movies on Amazon Prime Video have no way to bring their viewing history into the Movie Ranking app. This creates friction for new users who want to quickly populate their rankings with movies they've already watched, rather than manually searching for and adding each movie one by one.

Currently, users must:
1. Remember which movies they've watched on Prime
2. Search for each movie individually in the app
3. Add and rate each movie manually

This manual process is tedious and discourages users from fully adopting the app, especially those with extensive Prime viewing histories.

## Proposed Solution

### Overview

Implement a multi-step import workflow that allows users to upload a CSV export of their Amazon Prime Video watch history, match those movies against TMDB, and selectively add movies to their rankings with ratings.

### Key Components

1. **CSV File Upload**: A file input in the Settings page that accepts CSV files exported from Amazon Prime Video using third-party tools.

2. **CSV Parser**: Backend service to parse the Amazon Prime CSV format and extract movie data (filtering out TV series).

3. **TMDB Matcher**: Service that uses the existing TMDB integration to find matching movies by title and year.

4. **Import Session**: Temporary in-memory storage of parsed/matched movies for the duration of the import workflow.

5. **Review Workflow**: Step-by-step UI where users review each matched movie and decide to add (with rating) or skip.

### User Experience

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

## Technical Approach

### Backend Changes

#### New Router: `/api/v1/import/`

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

#### CSV Parsing Service

Parse Amazon Prime CSV format:
- **Date Watched**: Parse to datetime (format: varies by locale)
- **Type**: Filter for "Movie" only (skip "Series")
- **Title**: Movie title for TMDB search
- **Image URL**: Fallback poster if TMDB match fails

Expected CSV columns:
```
Date Watched,Type,Title,Episode Title,Global Title Identifier,Episode Global Title Identifier,Path,Episode Path,Image URL
```

#### TMDB Matching Strategy

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

#### Session Storage

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

### Frontend Changes

#### New Import Components

1. **ImportWizard**: Multi-step wizard container
2. **FileUploadStep**: CSV file selection and upload
3. **ReviewStep**: Movie-by-movie review interface
4. **CompletionStep**: Summary and next actions

#### State Management

Use local component state for the import wizard:
- Current step (upload, review, complete)
- Session ID from backend
- Current movie index
- Local cache of session data

#### Settings Page Integration

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

### Data Model

No new database tables required. Import sessions are temporary and in-memory. Movies and rankings use existing tables.

## Implementation Notes

### Dependencies

- Existing TMDB service for movie matching
- Existing rankings API for creating new rankings
- Existing movies API for creating new movies (if not exists)

### Integration Points

- **TMDBService**: Leverage existing `search_movies()` method
- **Rankings Router**: Use existing `create_or_update_ranking()` for adding movies
- **Movies Router**: Use existing `get_or_create_movie()` pattern

### Feature Flags

No feature flag needed for initial release. This is additive functionality in Settings.

### Rate Limiting Considerations

- TMDB API has rate limits (40 requests/10 seconds for free tier)
- Implementation: 1-second delay every 35 requests during batch matching
- Leverage existing `TMDBRateLimitError` handling in `TMDBService`
- Show progress indicator during matching phase (e.g., "Matching movie 15 of 47...")
- If rate limit hit, wait 2 seconds and retry once before marking as unmatched

## Testing Strategy

- **Unit tests:** CSV parser with various date formats and edge cases
- **Unit tests:** TMDB matching logic with mock responses
- **Integration tests:** Full upload-to-ranking flow
- **Manual testing:**
  - File with mixed movies and TV shows
  - File with movies already in user's rankings
  - File with movies that have no TMDB match
  - Large file (500+ entries)
  - Malformed CSV handling

## Rollback Plan

1. Remove import section from Settings page
2. Remove import router from FastAPI app
3. No database changes to revert

## Acceptance Criteria

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

## Open Questions (Resolved)

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

## Appendix

### Amazon Prime CSV Format

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

### References

- [Watch History Exporter for Amazon Prime Video (GitHub)](https://github.com/twocaretcat/watch-history-exporter-for-amazon-prime-video)
- [Prime Video History to CSV (Python)](https://github.com/gitzain/prime-video-history-to-csv)
- [Export script (JavaScript Gist)](https://gist.github.com/jerboa88/06cf269b9192802e2689d3850b79164c)
