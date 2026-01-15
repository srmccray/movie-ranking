# Movie Ranking Project Conventions

This document captures project conventions to ensure consistency across the codebase.

## API Conventions

### Trailing Slashes
**All API endpoints use trailing slashes.** This is critical for FastAPI's redirect behavior.

```python
# Correct
@router.post("/")
@router.get("/")
@router.delete("/{ranking_id}/")

# Wrong - will cause 404 errors
@router.delete("/{ranking_id}")
```

Frontend API calls must also include trailing slashes:
```typescript
// Correct
await fetch(`/api/v1/rankings/${id}/`, { method: 'DELETE' });

// Wrong
await fetch(`/api/v1/rankings/${id}`, { method: 'DELETE' });
```

### HTTP Status Codes
- `200` - Successful update
- `201` - Successful creation
- `204` - Successful deletion (no content)
- `401` - Not authenticated
- `403` - Not authorized (e.g., accessing another user's resource)
- `404` - Resource not found
- `422` - Validation error

## DateTime Handling

### Strategy: Naive UTC
The database uses `TIMESTAMP WITHOUT TIME ZONE` columns. All datetimes are stored as **naive UTC**.

### Client Input
Frontend sends ISO 8601 with timezone:
```typescript
// Frontend sends
new Date().toISOString()  // "2025-12-25T10:00:00.000Z"
```

### Backend Conversion
Always convert timezone-aware datetimes to naive UTC before storage:

```python
from datetime import datetime, timezone

def to_naive_utc(dt: datetime | None) -> datetime | None:
    """Convert a datetime to naive UTC datetime for database storage."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt
```

### Usage
```python
# In router/service code
rating.rated_at = to_naive_utc(request.rated_at) or datetime.utcnow()
```

## Database Conventions

### Column Types
- UUIDs: `UUID` with `server_default=text("gen_random_uuid()")`
- Timestamps: `DateTime(timezone=True)` in migrations, stored as naive UTC
- Strings: Use appropriate `String(length)` - see existing models for patterns

### Migrations
- Number migrations sequentially: `001_`, `002_`, etc.
- Backfill data when adding non-nullable columns
- Add indexes for frequently queried columns

## Testing Requirements

### API Tests Must:
1. Use trailing slashes in all URLs
2. Send timezone-aware dates (ISO 8601 with 'Z' suffix)
3. Test full data path: input → storage → retrieval
4. Include edge cases: nulls, boundaries, timezone variations

### Example Test Pattern
```python
@pytest.mark.asyncio
async def test_create_with_custom_date(self, client, auth_headers, test_movie):
    custom_date = "2025-12-25T10:00:00Z"  # Timezone-aware
    response = await client.post(
        "/api/v1/rankings/",  # Trailing slash
        json={
            "movie_id": test_movie["movie_id"],
            "rating": 4,
            "rated_at": custom_date,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
```

## Frontend Conventions

### API Client
- Always use trailing slashes on API calls
- Handle 204 No Content responses
- Send dates as ISO 8601 UTC: `new Date().toISOString()`

### Content-Type Headers
- JSON requests: `application/json` (default)
- Form data: `application/x-www-form-urlencoded` (login)
- Don't override Content-Type if already set

## API Contract Verification

**Critical:** Frontend and backend types must match exactly. Runtime errors occur when they don't.

### Common Pitfall
```typescript
// Backend returns: { results: [...], query: "...", year: null }
// WRONG - Frontend assumes raw array
async searchMovies(): Promise<SearchResult[]> {
  return this.request<SearchResult[]>('/search/');  // Runtime error!
}

// CORRECT - Frontend matches backend wrapper
async searchMovies(): Promise<SearchResult[]> {
  const response = await this.request<SearchResponse>('/search/');
  return response.results;
}
```

### Verification Checklist
- [ ] Read backend schema (`app/schemas/*.py`) before implementing frontend types
- [ ] Check `response_model=` in router to see exact response shape
- [ ] Wrapper responses (`*ListResponse`, `*SearchResponse`) contain data in a field like `items` or `results`
- [ ] Field names use `snake_case` (matching Python/JSON convention)

**See also:**
- `frontend/CLAUDE.md` → "API Contract Verification" section
- `app/CLAUDE.md` → "Frontend API Contract Documentation" section

## Planning Documents

All implementation plans are stored in `.claude/plans/`:

### Legacy Plans (single files)
- `01-initial-app-implementation.md` - Original app architecture
- `02-api-implementation.md` - FastAPI backend implementation
- `03-rating-date-and-delete-features.md` - Rating date and delete features
- `04-movie-search-feature.md` - TMDB movie search integration
- `05-frontend-development.md` - React frontend development
- `06-fix-date-timezone-bug.md` - Date timezone bug fix

### New Feature Plans (directory structure)
New features use a directory structure with the product-manager creating the feature plan and the tech-lead breaking it into tasks:

```
.claude/plans/NN-feature-name/
├── README.md           # Feature plan (created by product-manager)
├── TASKS.md            # Task execution plan (created by tech-lead)
├── 01-task-name.md     # Individual task with agent assignment
├── 02-task-name.md
└── ...
```

**Active Feature Plans:**
- `07-analytics-enhancements/` - 2x2 dashboard with stats card and rating distribution chart

### Workflow
1. **product-manager** creates `README.md` with feature definition, user stories, and requirements
2. **tech-lead** reviews the plan and creates task files with agent assignments
3. Tasks are executed by assigned agents in the defined sequence

## Git Commit Messages

- Do NOT include "Co-Authored-By: Claude" or any Claude attribution in commit messages
- Keep commit messages concise and descriptive
- Use present tense ("Add feature" not "Added feature")

## Before Implementing New Features

### Checklist
- [ ] Examine 3+ similar implementations in the codebase
- [ ] Review models, schemas, routers, and migrations for related features
- [ ] Document conventions found (URL patterns, datetime handling, etc.)
- [ ] Verify trailing slash convention matches existing endpoints
- [ ] Match datetime handling patterns (naive UTC conversion)
- [ ] Write integration tests with realistic frontend requests
