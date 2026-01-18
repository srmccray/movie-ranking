# Task 04: Frontend API Client and Types

**Feature:** amazon-prime-import
**Agent:** frontend-implementation
**Status:** Not Started
**Blocked By:** 03

---

## Objective

Add TypeScript type definitions for the import feature and implement API client methods for all import endpoints.

---

## Context

The backend import endpoints are now available. The frontend needs matching TypeScript types and API client methods to interact with the import workflow.

### Relevant FRD Sections
- FRD Section: "API Design" - Request/response structures

### Relevant Refinement Notes
- Frontend types must match backend schemas exactly (API contract verification)
- Use snake_case for field names to match backend JSON

---

## Scope

### In Scope
- Add import-related types to `frontend/src/types/index.ts`
- Add import API methods to `frontend/src/api/client.ts`

### Out of Scope
- UI components (task-05)
- Backend changes (tasks 01-03)

---

## Implementation Notes

### Key Files

| File | Action | Notes |
|------|--------|-------|
| `/Users/stephen/Projects/movie-ranking/frontend/src/types/index.ts` | Modify | Add import types |
| `/Users/stephen/Projects/movie-ranking/frontend/src/api/client.ts` | Modify | Add import API methods |

### Patterns to Follow

- Type definitions: See existing types in `/Users/stephen/Projects/movie-ranking/frontend/src/types/index.ts`
- API client: See existing methods in `/Users/stephen/Projects/movie-ranking/frontend/src/api/client.ts`

### Type Definitions

Add to `/Users/stephen/Projects/movie-ranking/frontend/src/types/index.ts`:

```typescript
// ============================================
// Amazon Prime Import Types
// ============================================

/**
 * A movie parsed from the Amazon Prime CSV file.
 */
export interface ParsedMovieItem {
  title: string;
  watch_date: string | null;  // ISO 8601 or null
  prime_image_url: string | null;
}

/**
 * TMDB search result for import matching.
 */
export interface TMDBMatchResult {
  tmdb_id: number;
  title: string;
  year: number | null;
  poster_url: string | null;
  overview: string | null;
}

/**
 * A parsed movie with TMDB match results.
 */
export interface MatchedMovieItem {
  parsed: ParsedMovieItem;
  tmdb_match: TMDBMatchResult | null;
  confidence: number;  // 0.0 - 1.0
  alternatives: TMDBMatchResult[];
  status: 'pending' | 'added' | 'skipped';
}

/**
 * Response after uploading Amazon Prime CSV file.
 * POST /api/v1/import/amazon-prime/upload/
 */
export interface ImportSessionResponse {
  session_id: string;
  total_entries: number;
  movies_found: number;
  tv_shows_filtered: number;
  already_ranked: number;
  ready_for_review: number;
  movies: MatchedMovieItem[];
}

/**
 * Current import session state.
 * GET /api/v1/import/amazon-prime/session/{session_id}/
 */
export interface ImportSessionDetailResponse {
  session_id: string;
  current_index: number;
  total_movies: number;
  added_count: number;
  skipped_count: number;
  remaining_count: number;
  movies: MatchedMovieItem[];
}

/**
 * Request to add a movie from import session.
 * POST /api/v1/import/amazon-prime/session/{session_id}/movie/{index}/add/
 */
export interface ImportMovieAddRequest {
  rating: number;  // 1-5
  rated_at?: string | null;  // ISO 8601, optional
}

/**
 * Summary after completing import (computed from session state).
 */
export interface ImportCompletionSummary {
  movies_added: number;
  movies_skipped: number;
  unmatched_titles: string[];
}
```

### API Client Methods

Add to `/Users/stephen/Projects/movie-ranking/frontend/src/api/client.ts`:

```typescript
// Import the new types at the top
import type {
  // ... existing imports
  ImportSessionResponse,
  ImportSessionDetailResponse,
  ImportMovieAddRequest,
  Ranking,
} from '../types';

// Add these methods to the ApiClient class:

  // ============================================
  // Amazon Prime Import Methods
  // ============================================

  /**
   * Upload an Amazon Prime CSV file to start an import session.
   * @param file - The CSV file to upload
   * @returns Import session with matched movies
   */
  async uploadAmazonPrimeCSV(file: File): Promise<ImportSessionResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${this.baseUrl}/import/amazon-prime/upload/`, {
      method: 'POST',
      headers: {
        ...this.getAuthHeaders(),
        // Note: Don't set Content-Type for FormData - browser sets it with boundary
      },
      body: formData,
    });

    if (!response.ok) {
      await this.handleError(response);
    }

    return response.json();
  }

  /**
   * Get the current state of an import session.
   * @param sessionId - The session ID from upload response
   * @returns Current session state with progress
   */
  async getImportSession(sessionId: string): Promise<ImportSessionDetailResponse> {
    return this.request<ImportSessionDetailResponse>(
      `/import/amazon-prime/session/${sessionId}/`
    );
  }

  /**
   * Add a movie from the import session to user's rankings.
   * @param sessionId - The session ID
   * @param movieIndex - Index of the movie in the session
   * @param rating - Rating to assign (1-5)
   * @param ratedAt - Optional rated_at timestamp (ISO 8601)
   * @returns The created ranking
   */
  async addImportMovie(
    sessionId: string,
    movieIndex: number,
    rating: number,
    ratedAt?: string
  ): Promise<Ranking> {
    const body: ImportMovieAddRequest = { rating };
    if (ratedAt) {
      body.rated_at = ratedAt;
    }

    return this.request<Ranking>(
      `/import/amazon-prime/session/${sessionId}/movie/${movieIndex}/add/`,
      {
        method: 'POST',
        body: JSON.stringify(body),
      }
    );
  }

  /**
   * Skip a movie in the import session.
   * @param sessionId - The session ID
   * @param movieIndex - Index of the movie to skip
   */
  async skipImportMovie(sessionId: string, movieIndex: number): Promise<void> {
    await this.request<void>(
      `/import/amazon-prime/session/${sessionId}/movie/${movieIndex}/skip/`,
      { method: 'POST' }
    );
  }

  /**
   * Cancel and delete an import session.
   * @param sessionId - The session ID to cancel
   */
  async cancelImportSession(sessionId: string): Promise<void> {
    await this.request<void>(
      `/import/amazon-prime/session/${sessionId}/`,
      { method: 'DELETE' }
    );
  }
```

### Technical Decisions

- **FormData for upload:** Browser automatically sets correct multipart/form-data Content-Type with boundary
- **Direct fetch for upload:** FormData requires different handling than JSON requests
- **Optional rated_at:** Only include in body if provided to let backend use watch_date default

---

## Acceptance Criteria

- [ ] ParsedMovieItem type matches backend schema
- [ ] TMDBMatchResult type matches backend schema
- [ ] MatchedMovieItem type matches backend schema
- [ ] ImportSessionResponse type matches backend schema
- [ ] ImportSessionDetailResponse type matches backend schema
- [ ] ImportMovieAddRequest type matches backend schema
- [ ] uploadAmazonPrimeCSV() correctly uploads file as FormData
- [ ] getImportSession() fetches session state
- [ ] addImportMovie() creates ranking with rating
- [ ] addImportMovie() optionally includes rated_at
- [ ] skipImportMovie() marks movie as skipped
- [ ] cancelImportSession() deletes the session
- [ ] All API methods use trailing slashes in URLs
- [ ] All API methods include auth headers

---

## Testing Requirements

- [ ] Add MSW handlers for import endpoints in test mocks
- [ ] Test uploadAmazonPrimeCSV with mock file
- [ ] Test getImportSession response parsing
- [ ] Test addImportMovie with and without rated_at
- [ ] Test skipImportMovie
- [ ] Test cancelImportSession
- [ ] Test error handling for 404 (session expired)

---

## Handoff Notes

### For Next Task (task-05)
- All types are available via `import type { ... } from '../types'`
- All API methods available via `apiClient.uploadAmazonPrimeCSV()`, etc.
- ImportCompletionSummary can be computed from session state in UI

### Artifacts Produced
- Modified `/Users/stephen/Projects/movie-ranking/frontend/src/types/index.ts`
- Modified `/Users/stephen/Projects/movie-ranking/frontend/src/api/client.ts`
