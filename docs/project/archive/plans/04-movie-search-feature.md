# Movie Search Feature Implementation Plan

## Executive Summary

Add movie search functionality that allows users to search for movies from an external movie database (TMDB) instead of manually typing movie titles. This improves data quality and user experience by providing accurate movie information including titles, years, and potentially additional metadata.

---

## 1. Product Requirements (Product Manager Analysis)

### User Stories

1. **As a user, I want to search for movies by title** so that I don't have to type the exact movie name and year manually.

2. **As a user, I want to see search results with movie posters and release years** so that I can easily identify the correct movie.

3. **As a user, I want to select a movie from search results** so that the correct movie details are automatically populated.

4. **As a user, I want a fallback to manual entry** so that I can still add movies that might not be in the database.

### Acceptance Criteria

- Search input with debounced API calls (300ms delay)
- Display up to 10 search results per query
- Each result shows: movie title, release year, poster thumbnail (if available)
- Clicking a result populates the movie form fields
- Clear indication when no results found
- Loading state during search
- Error handling for API failures with graceful degradation to manual entry
- Manual entry option always available (toggle or fallback)

### Out of Scope (Phase 1)

- Storing additional movie metadata (director, cast, runtime)
- Movie poster storage in our database
- Auto-complete/typeahead while typing
- Search history or suggestions

---

## 2. Technical Analysis & API Selection

### API Options Evaluation

| API | Pros | Cons | Cost |
|-----|------|------|------|
| **TMDB (The Movie Database)** | Free tier, excellent data quality, widely used, good documentation, includes images | Requires API key, attribution required | Free (with attribution) |
| **OMDB API** | Simple API, IMDB IDs available | Limited free tier (1000 req/day), less comprehensive | Free limited / $1-2/mo |
| **IMDB** | Most authoritative | No public API, would require scraping | N/A |

### Recommendation: TMDB API

**Rationale:**
- Free tier with generous limits (sufficient for personal use)
- Excellent search functionality
- Provides movie posters, release dates, and TMDB IDs
- Well-documented REST API
- Industry standard for movie apps

### TMDB API Details

- **Search endpoint**: `GET /search/movie?query={title}&year={year}`
- **Base URL**: `https://api.themoviedb.org/3`
- **Image base URL**: `https://image.tmdb.org/t/p/w92` (for thumbnails)
- **Authentication**: API key via query parameter or Bearer token
- **Rate limits**: 40 requests per 10 seconds

---

## 3. Architecture Design

### Data Flow

```
User Types Search → Frontend Debounces → Backend Proxy → TMDB API
                                                            ↓
User Selects Movie ← Frontend Displays ← Backend Returns ← Search Results
        ↓
Form Populated with TMDB data → User adds rating → Existing create flow
```

### Why Backend Proxy?

1. **API Key Security**: TMDB API key stays server-side
2. **Rate Limiting Control**: Can implement our own rate limiting
3. **Response Shaping**: Return only needed fields
4. **Caching Potential**: Can cache popular searches (future)
5. **CORS**: Avoid browser CORS issues

### Database Changes

**Option A: No changes (Recommended for Phase 1)**
- Store only title and year as currently done
- TMDB search is purely for UX convenience
- Simpler, no migration needed

**Option B: Store TMDB ID (Future consideration)**
- Add `tmdb_id` column to movies table
- Enables future features (fetch additional metadata, deduplication)
- Requires migration

**Recommendation**: Start with Option A, consider Option B as a future enhancement.

---

## 4. Implementation Plan

### Phase 1: Backend Implementation

#### 4.1 Configuration Updates

**File**: `/Users/stephen/Projects/movie-ranking/app/config.py`

Add new settings:
```python
TMDB_API_KEY: str | None = None  # Optional, feature disabled if not set
TMDB_BASE_URL: str = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL: str = "https://image.tmdb.org/t/p/w92"
```

#### 4.2 New Schemas

**File**: `/Users/stephen/Projects/movie-ranking/app/schemas/movie.py`

Add new schemas:
```python
class TMDBMovieResult(BaseModel):
    """Movie result from TMDB search."""
    tmdb_id: int
    title: str
    year: int | None
    poster_url: str | None
    overview: str | None

class TMDBSearchResponse(BaseModel):
    """Response for movie search."""
    results: list[TMDBMovieResult]
    total_results: int
```

#### 4.3 New Service Layer

**File**: `/Users/stephen/Projects/movie-ranking/app/services/tmdb.py` (new)

Create TMDB service:
- `search_movies(query: str, year: int | None = None) -> TMDBSearchResponse`
- Handle API errors gracefully
- Transform TMDB response to our schema
- Use httpx for async HTTP requests

#### 4.4 New Router Endpoint

**File**: `/Users/stephen/Projects/movie-ranking/app/routers/movies.py`

Add search endpoint:
```python
@router.get("/search/")
async def search_movies(
    query: str = Query(..., min_length=1, max_length=100),
    year: int | None = Query(None, ge=1888, le=2031),
    current_user: CurrentUser,
) -> TMDBSearchResponse:
    """Search movies from TMDB."""
```

### Phase 2: Frontend Implementation

#### 4.5 New Types

**File**: `/Users/stephen/Projects/movie-ranking/frontend/src/types/index.ts`

```typescript
export interface TMDBMovieResult {
  tmdb_id: number;
  title: string;
  year: number | null;
  poster_url: string | null;
  overview: string | null;
}

export interface TMDBSearchResponse {
  results: TMDBMovieResult[];
  total_results: number;
}
```

#### 4.6 API Client Updates

**File**: `/Users/stephen/Projects/movie-ranking/frontend/src/api/client.ts`

Add method:
```typescript
async searchMovies(query: string, year?: number): Promise<TMDBSearchResponse>
```

#### 4.7 New Search Component

**File**: `/Users/stephen/Projects/movie-ranking/frontend/src/components/MovieSearch.tsx` (new)

Features:
- Search input with debounce (300ms)
- Results dropdown with poster thumbnails
- Loading spinner during search
- "No results" and error states
- Click to select movie
- Keyboard navigation (up/down arrows, enter to select)
- "Can't find your movie? Add manually" link

#### 4.8 Updated AddMovieForm

**File**: `/Users/stephen/Projects/movie-ranking/frontend/src/components/AddMovieForm.tsx`

Changes:
- Add mode toggle: Search / Manual Entry
- Integrate MovieSearch component
- When movie selected from search, populate title/year fields
- Keep existing validation and submission logic

### Phase 3: Testing

#### 4.9 Backend Tests

**File**: `/Users/stephen/Projects/movie-ranking/tests/test_movie_search.py` (new)

- Test search endpoint requires authentication
- Test search with valid query returns results
- Test search with no results returns empty array
- Test search handles TMDB API errors gracefully
- Test rate limiting behavior (if implemented)

#### 4.10 Frontend Tests

- Test MovieSearch component renders
- Test debounce behavior
- Test keyboard navigation
- Test selection callback
- Mock MSW handlers for search endpoint

---

## 5. File Changes Summary

### New Files

| File | Purpose |
|------|---------|
| `/Users/stephen/Projects/movie-ranking/app/services/__init__.py` | Services module init |
| `/Users/stephen/Projects/movie-ranking/app/services/tmdb.py` | TMDB API integration service |
| `/Users/stephen/Projects/movie-ranking/frontend/src/components/MovieSearch.tsx` | Search UI component |
| `/Users/stephen/Projects/movie-ranking/frontend/src/hooks/useMovieSearch.ts` | Search hook with debounce |
| `/Users/stephen/Projects/movie-ranking/tests/test_movie_search.py` | Backend search tests |

### Modified Files

| File | Changes |
|------|---------|
| `/Users/stephen/Projects/movie-ranking/app/config.py` | Add TMDB config settings |
| `/Users/stephen/Projects/movie-ranking/app/schemas/movie.py` | Add search response schemas |
| `/Users/stephen/Projects/movie-ranking/app/routers/movies.py` | Add search endpoint |
| `/Users/stephen/Projects/movie-ranking/frontend/src/types/index.ts` | Add search types |
| `/Users/stephen/Projects/movie-ranking/frontend/src/api/client.ts` | Add search method |
| `/Users/stephen/Projects/movie-ranking/frontend/src/components/AddMovieForm.tsx` | Integrate search |
| `/Users/stephen/Projects/movie-ranking/frontend/src/components/index.ts` | Export MovieSearch |
| `/Users/stephen/Projects/movie-ranking/requirements.txt` | Add httpx dependency |

---

## 6. Dependencies

### Backend

```
httpx>=0.25.0  # Async HTTP client for TMDB API calls
```

### Frontend

No new dependencies - using native fetch with existing patterns.

---

## 7. Environment Setup

User needs to:
1. Register for a TMDB API key at https://www.themoviedb.org/settings/api
2. Add to `.env` file:
   ```
   TMDB_API_KEY=your_api_key_here
   ```

The feature should gracefully degrade if API key is not configured (show manual entry only).

---

## 8. Implementation Sequence

### Recommended Order

1. **Backend Config & Service** - Add TMDB integration (can test with curl)
2. **Backend Endpoint & Tests** - Expose search API
3. **Frontend Types & API Client** - Connect to backend
4. **MovieSearch Component** - Build search UI
5. **Integrate into AddMovieForm** - Wire everything together
6. **Frontend Tests** - Add MSW handlers and component tests
7. **Documentation** - Update CLAUDE.md with new patterns

### Estimated Effort

| Task | Estimate |
|------|----------|
| Backend (config, service, endpoint, tests) | 2-3 hours |
| Frontend (types, client, components, integration) | 3-4 hours |
| Testing & Polish | 1-2 hours |
| **Total** | **6-9 hours** |

---

## 9. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| TMDB API changes | Abstract behind service layer, easy to swap |
| Rate limiting | Add caching layer if needed (future) |
| No API key configured | Graceful fallback to manual entry |
| Slow TMDB response | Loading states, timeout handling |
| User adds duplicate movies | Out of scope for Phase 1, consider deduplication later |

---

## 10. Success Metrics

- Users can find and select movies via search
- Search results appear within 1 second of typing
- Manual entry remains available as fallback
- No errors when TMDB is unavailable (graceful degradation)

---

## 11. Questions for User Before Proceeding

1. **TMDB API Key**: Do you already have a TMDB API key, or would you like instructions on how to obtain one?

2. **Scope Confirmation**: Are you comfortable with Phase 1 scope (search for convenience, no metadata storage), or do you want to store TMDB IDs for future use?

3. **Image Display**: Do you want poster thumbnails in search results (requires image proxy considerations)?

4. **Manual Entry Default**: Should the form default to search mode or manual entry mode?
