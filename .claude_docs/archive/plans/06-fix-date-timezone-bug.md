# Fix Date Timezone Bug

## Problem
When entering "1/1/26" as a rated date, it displays as "Dec 31, 2025". This is a timezone conversion issue.

## Root Cause
In `frontend/src/components/MovieCard.tsx` line 62:
```typescript
const isoDate = new Date(editedDate).toISOString();
```

When `editedDate` is `"2026-01-01"` (from HTML date input), JavaScript interprets it as **midnight in the local timezone**. Then `toISOString()` converts to UTC, shifting the time. For users in PST (UTC-8):
- Input: "2026-01-01" → interpreted as Jan 1, 2026 00:00 PST
- Converted to UTC: Jan 1, 2026 08:00 UTC
- Stored in database: 2026-01-01T08:00:00
- Displayed: The UTC time converted back to local shows Dec 31, 2025 at 4 PM

## Fix
Treat the user-entered date as a calendar date (midnight UTC), not a local datetime.

### Files to Modify

#### 1. `frontend/src/components/MovieCard.tsx`
**Line 62** - Change date-to-ISO conversion:
```typescript
// Before
const isoDate = new Date(editedDate).toISOString();

// After - interpret as midnight UTC
const isoDate = new Date(editedDate + 'T00:00:00Z').toISOString();
```

#### 2. `frontend/src/components/AddMovieForm.tsx`
**Lines 21-23** - Fix `getTodayString()` to use local date components:
```typescript
// Before
function getTodayString(): string {
  return new Date().toISOString().split('T')[0];
}

// After - use local date components
function getTodayString(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}
```

#### 3. `frontend/src/hooks/useRankings.ts`
**Line 75** - Fix date conversion in `addMovieAndRank`:
```typescript
// Before
rated_at: ratedAt ? new Date(ratedAt).toISOString() : undefined,

// After
rated_at: ratedAt ? new Date(ratedAt + 'T00:00:00Z').toISOString() : undefined,
```

## Verification
1. Start the frontend dev server: `cd frontend && npm run dev`
2. Log in and edit an existing movie's rated date to "1/1/26"
3. Verify it displays as "Jan 1, 2026" (not Dec 31, 2025)
4. Add a new movie with today's date
5. Verify the date displays correctly
6. Run frontend tests: `npm run test:run`
