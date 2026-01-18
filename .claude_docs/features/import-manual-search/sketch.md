# Quick Sketch: Manual Movie Search in Amazon Prime Import Wizard

**Created:** 2026-01-17
**Tier:** SMALL
**Triage Scores:** Complexity 3/10, Risk 2/10

## What

Add the ability for users to manually search for and select a TMDB movie match during the Amazon Prime import review step, enabling correction of wrong matches and resolution of unmatched movies.

## Why

When importing Amazon Prime watch history, automatic TMDB matching sometimes fails:
1. The automatic match is incorrect (e.g., wrong year, different movie with same title)
2. No match is found at all (especially for less popular or international films)

Currently, users can only skip unmatched movies and must manually add them later. This friction causes incomplete imports and poor user experience.

## Approach

1. **Frontend - Add search trigger to ImportReview component:**
   - Add "Search" button for matched movies with low/medium confidence
   - Add "Search for this movie" action for unmatched movies (replaces current skip-only flow)
   - Show inline `MovieSearch` component when triggered

2. **Frontend - Handle movie selection:**
   - When user selects a movie from search results, call new PATCH endpoint
   - Update local state to reflect the new match
   - Return to rating flow with the newly selected movie

3. **Backend - Add PATCH endpoint to update movie match:**
   - `PATCH /api/v1/import/amazon-prime/session/{session_id}/movie/{index}/match/`
   - Accept `tmdb_id` to set as the new match
   - Fetch movie details from TMDB and update session in-memory
   - Return updated `MatchedMovieItem`

## Files Likely Affected

- `/Users/stephen/Projects/movie-ranking/frontend/src/components/ImportReview.tsx` - Add search UI, state management for search mode, selection handler
- `/Users/stephen/Projects/movie-ranking/frontend/src/api/client.ts` - Add `updateImportMovieMatch(sessionId, index, tmdbId)` method
- `/Users/stephen/Projects/movie-ranking/frontend/src/types/index.ts` - Add `UpdateMatchRequest` interface
- `/Users/stephen/Projects/movie-ranking/app/routers/import_amazon.py` - Add PATCH endpoint for updating match
- `/Users/stephen/Projects/movie-ranking/app/schemas/import_amazon.py` - Add `UpdateMatchRequest` schema

## Considerations

- **Reuse existing MovieSearch component:** The `MovieSearch` component already handles debounced search, keyboard navigation, and result selection. Pass an `onSelect` callback that updates the import session.
- **In-memory session updates:** Sessions are stored in-memory in `import_session_store`. The new endpoint just updates the session dictionary - no database changes needed.
- **TMDB rate limits:** The PATCH endpoint will make one TMDB API call to fetch movie details. This is a single call per user action, so rate limiting is not a concern.
- **Confidence reset:** When manually selecting a movie, set confidence to 1.0 to indicate user-confirmed match.
- **Clear alternatives:** After manual selection, clear the `alternatives` array since the user made an explicit choice.

## Acceptance Criteria

- [ ] Users can click "Search" on a matched movie to search for a different match
- [ ] Users can click "Search for this movie" on unmatched movies to find a match
- [ ] Search results display in the same style as the main MovieSearch component
- [ ] Selecting a search result updates the current movie's match in the session
- [ ] After selection, the review UI shows the newly matched movie for rating
- [ ] Users can cancel the search and return to the previous state
- [ ] Previously unmatched movies become ratable after a match is selected

---

## Next Agent to Invoke

**Agent:** `frd-refiner`

**Context to provide:**
- Feature slug: `import-manual-search`
- Tier: SMALL
- Sketch location: `/Users/stephen/Projects/movie-ranking/.claude_docs/features/import-manual-search/sketch.md`
- This is a straightforward feature with clear scope - refinement should be light

**After that agent completes:**
The FRD Refiner will validate the sketch against the codebase and may add implementation details. After refinement, proceed to `frontend-implementation` (primary changes are in the frontend) followed by `backend-implementation` for the new PATCH endpoint.
