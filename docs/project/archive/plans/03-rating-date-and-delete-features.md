# Plan: Add Rating Date and Delete Ranking Features

## Overview
Add two features to the Movie Ranking application:
1. **Custom Rating Date**: Allow users to set when they rated a movie (defaults to today)
2. **Delete Ranking**: Allow users to delete their movie rankings

---

## Feature 1: Custom Rating Date

### Design Decision
- Add new `rated_at` field (separate from `updated_at`)
- When updating a rating, do NOT auto-update `rated_at` (user must explicitly change it)
- `rated_at` represents "when I watched this" - a historical fact that shouldn't change with rating tweaks

### Backend Changes

**1. Database Migration** - Create `alembic/versions/002_add_rated_at.py`
- Add `rated_at` column with default `CURRENT_TIMESTAMP`
- Backfill existing rows: `SET rated_at = created_at`
- Add index on `(user_id, rated_at DESC)`

**2. Model** - `app/models/ranking.py`
- Add field: `rated_at: Mapped[datetime]` after line 60

**3. Schemas** - `app/schemas/ranking.py`
- `RankingCreate`: Add `rated_at: datetime | None = None`
- `RankingResponse`: Add `rated_at: datetime`
- `RankingWithMovie`: Add `rated_at: datetime`

**4. Router** - `app/routers/rankings.py`
- `create_or_update_ranking`: Use `rated_at` from request or default to `datetime.utcnow()`
- On update: Only change `rated_at` if explicitly provided
- Change list sort order to `rated_at.desc()` instead of `updated_at`

### Frontend Changes

**1. Types** - `frontend/src/types/index.ts`
- Add `rated_at: string` to `Ranking`, `RankingWithMovie`
- Add `rated_at?: string` to `RankingCreate`

**2. AddMovieForm** - `frontend/src/components/AddMovieForm.tsx`
- Add date input (type="date") defaulting to today
- Update props: `onSubmit: (movie, rating, ratedAt?) => Promise<void>`

**3. MovieCard** - `frontend/src/components/MovieCard.tsx`
- Display `rated_at` instead of `updated_at`

**4. useRankings Hook** - `frontend/src/hooks/useRankings.ts`
- Update `addMovieAndRank(movie, rating, ratedAt?)`
- Pass `rated_at` to API client

**5. RankingsPage** - `frontend/src/pages/RankingsPage.tsx`
- Update `handleAddMovie` to pass date

---

## Feature 2: Delete Ranking

### Backend Changes

**1. Router** - `app/routers/rankings.py`
Add new endpoint after existing ones:
```python
@router.delete("/{ranking_id}", status_code=204)
async def delete_ranking(ranking_id: UUID, current_user: CurrentUser, db: DbSession):
    # Find ranking, verify ownership, delete
```
- Return 404 if not found
- Return 403 if user doesn't own the ranking
- Return 204 on success

### Frontend Changes

**1. API Client** - `frontend/src/api/client.ts`
- Add method: `deleteRanking(rankingId: string): Promise<void>`
- Update `request()` to handle 204 No Content responses

**2. useRankings Hook** - `frontend/src/hooks/useRankings.ts`
- Add `deleteRanking(rankingId)` method
- Remove from local state after successful delete

**3. MovieCard** - `frontend/src/components/MovieCard.tsx`
- Add `onDelete?: (rankingId: string) => void` prop
- Add delete button (trash icon)
- Add confirmation dialog before deleting

**4. RankingsPage** - `frontend/src/pages/RankingsPage.tsx`
- Add `handleDelete` callback
- Pass `onDelete` prop to MovieCard
- Add error display for delete failures

**5. CSS** - `frontend/src/index.css`
- Add styles for delete button and confirmation dialog

---

## Files to Modify

| File | Changes |
|------|---------|
| `alembic/versions/002_add_rated_at.py` | Create - migration for rated_at |
| `app/models/ranking.py` | Add rated_at field |
| `app/schemas/ranking.py` | Add rated_at to schemas |
| `app/routers/rankings.py` | Handle rated_at, add DELETE endpoint |
| `frontend/src/types/index.ts` | Add rated_at to types |
| `frontend/src/api/client.ts` | Add deleteRanking, handle 204 |
| `frontend/src/hooks/useRankings.ts` | Add deleteRanking, update addMovieAndRank |
| `frontend/src/components/AddMovieForm.tsx` | Add date picker |
| `frontend/src/components/MovieCard.tsx` | Show rated_at, add delete button |
| `frontend/src/pages/RankingsPage.tsx` | Wire up delete handler |
| `frontend/src/index.css` | Add delete button/dialog styles |

---

## Implementation Order

1. **Backend: Migration** - Create and run migration
2. **Backend: Model + Schemas** - Add rated_at field
3. **Backend: Router** - Update POST, add DELETE
4. **Backend: Tests** - Add tests for new functionality
5. **Frontend: Types + API** - Update types, add deleteRanking
6. **Frontend: Components** - Update AddMovieForm, MovieCard
7. **Frontend: Hook + Page** - Wire everything together
8. **Frontend: Styles** - Add CSS for delete UI

---

## Verification

### Manual Testing
1. **Rating Date**:
   - Add a movie with default date (should be today)
   - Add a movie with custom past date
   - Verify date displays correctly in MovieCard
   - Update rating, verify rated_at doesn't change

2. **Delete Ranking**:
   - Click delete button on a movie
   - Verify confirmation dialog appears
   - Cancel and verify movie still exists
   - Confirm delete and verify movie removed
   - Verify cannot delete another user's ranking (403)

### Automated Tests
```bash
# Backend
docker compose exec api pytest tests/test_rankings.py -v

# Frontend
cd frontend && npm test
```
