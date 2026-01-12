# Retrospective: Ranking Feature Bugs
**Date:** 2026-01-12
**Features:** Custom Rating Date, Delete Ranking

## Executive Summary

Two bugs occurred during the implementation of new ranking features. Both share a common theme: **failure to observe and follow existing patterns in the codebase**.

---

## Bug 1: Trailing Slash Issue (DELETE Endpoint)

### What Happened
- Added DELETE endpoint at `/{ranking_id}` (no trailing slash)
- All other endpoints use trailing slashes: `POST /`, `GET /`
- Frontend called `/rankings/{id}/` with trailing slash
- FastAPI redirect behavior with DELETE requests caused 404 errors

### Root Cause
1. **Pattern Blindness**: Didn't examine existing endpoints for conventions
2. **No Enforcement**: No automated check for URL pattern consistency
3. **Incomplete Testing**: Tests didn't simulate frontend behavior

### Fix Applied
Changed route from `"/{ranking_id}"` to `"/{ranking_id}/"` in both backend and frontend.

---

## Bug 2: Timezone Mismatch (rated_at Field)

### What Happened
- Added `rated_at` datetime field for user-provided timestamps
- Frontend sends ISO 8601 with 'Z' suffix (timezone-aware UTC)
- Database column is `TIMESTAMP WITHOUT TIME ZONE`
- SQLAlchemy error: "can't subtract offset-naive and offset-aware datetimes"
- Result: 500 Internal Server Error

### Root Cause
1. **Inconsistent Strategy**: Database schema uses timezone-aware types, but code uses naive datetimes (`datetime.utcnow()`)
2. **No Documentation**: No documented decision about timezone handling
3. **Missing Integration Test**: No test for full frontend → API → database flow

### Fix Applied
Added `to_naive_utc()` helper function to convert timezone-aware datetimes to naive UTC before storage.

---

## Prevention Checklist

### Before Writing Code
- [ ] Examine 3+ similar implementations in the codebase
- [ ] Review models, schemas, routers, and migrations for related features
- [ ] Document conventions found (URL patterns, datetime handling, etc.)

### When Adding API Endpoints
- [ ] Verify trailing slash convention matches existing endpoints
- [ ] Confirm correct HTTP status codes
- [ ] Match existing error response structure

### When Adding Database Fields
- [ ] Match conventions for similar fields (varchar lengths, datetime types)
- [ ] Use same patterns for defaults and server defaults
- [ ] Convert all client datetimes to naive UTC before storage

### Testing Requirements
- [ ] Test full flow from API input to database to API output
- [ ] Use trailing slashes in test URLs (matching frontend)
- [ ] Test timezone-aware dates, nulls, boundary values

---

## Agent Prompt Improvements

### Backend Engineer
```
Before implementing any new feature:
1. Read at least 3 existing endpoints in the same router. Follow trailing slash convention exactly.
2. Check how existing datetime fields handle timezone conversion. Convert client datetimes to naive UTC.
3. Review existing migrations for column type patterns.
4. Every new endpoint must have integration tests with realistic frontend requests.
```

### Frontend Engineer
```
1. Always use trailing slashes on API calls: DELETE /api/v1/rankings/${id}/
2. Send dates as ISO 8601 UTC: new Date().toISOString()
```

### QA Engineer
```
1. All API tests must use trailing slashes and ISO 8601 dates with 'Z' suffix
2. Test full data path: input → storage → retrieval
3. Include edge cases: nulls, boundaries, timezone variations
```

### Tech Lead
```
Before implementation, have backend engineer report on:
- URL structure (trailing slashes, path parameters)
- DateTime handling (timezone strategy)
- Error response format

Before marking complete, verify:
- Frontend and backend agree on URL formats
- DateTime serialization works end-to-end
- Integration tests cover full data flow
```

---

## Key Takeaways

| Bug | Root Cause | Prevention |
|-----|-----------|------------|
| Trailing Slash | Didn't follow URL conventions | Pattern discovery + integration tests with realistic URLs |
| Timezone | Undocumented datetime strategy | Document strategy + test with timezone-aware input |

**Main Lesson**: Both bugs would have been prevented by disciplined pattern discovery before implementation and integration tests that simulate realistic frontend behavior.
