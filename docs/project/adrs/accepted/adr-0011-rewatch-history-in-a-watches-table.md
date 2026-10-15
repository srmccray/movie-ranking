---
id: ADR-0011
title: Rewatch History Lives in a watches Table; rankings Keeps the Current Rating
status: Accepted
date: '2026-10-14'
---

# ADR-0011: Rewatch History Lives in a watches Table; rankings Keeps the Current Rating

## Status
Accepted

## Context
`rankings` has `UNIQUE(user_id, movie_id)` (`app/models/ranking.py`, constraint `uq_user_movie`; migration 001) and both write paths upsert: `POST /api/v1/rankings/` (`app/routers/rankings.py:84-115`) overwrites `rating` and optionally `rated_at`, and the import `add` endpoint (`app/routers/import_amazon/review.py:196-211`) overwrites `rating` and `rated_at` unconditionally. A rewatch therefore destroys the earlier rating and date, and activity and streak analytics (`app/routers/analytics.py`, `cast(Ranking.rated_at, Date)`) see only the latest date. The product owner has decided that rewatches must not overwrite old ratings.

## Decision
1. Add a new table **`watches`**: `id` (UUID PK, `gen_random_uuid()`), `user_id` (FK users, ON DELETE CASCADE), `movie_id` (FK movies, ON DELETE CASCADE), `watched_at` (naive UTC, per ADR-0010), `rating` (integer 1-5 with the same CHECK as rankings, nullable), `note` (TEXT, nullable), `source` (VARCHAR, `manual` by default, `amazon_prime` for imports), `created_at`. Indexes: `(user_id, watched_at DESC)` and `(user_id, movie_id, watched_at DESC)`. There is no unique constraint on `(user_id, movie_id)`, so multiple watches are allowed.
2. **`rankings` stays one row per user and movie** and continues to mean "current rating and last watched", always equal to the watch with the greatest `watched_at`. Writes that record a *viewing* append a watch: a new explicit rewatch endpoint (`POST /rankings/{id}/watches/`) and the Amazon import when the title is already ranked. The existing upsert `POST /rankings/` keeps its meaning of *correcting* the current rating or date (the frontend's inline edit controls call it) and updates the newest watch instead of appending, so editing a rating is not recorded as a rewatch. Existing endpoints and response shapes keep working (the API change is additive).
3. Deleting a ranking (`DELETE /rankings/{id}/` or `DELETE /rankings/all/`) also deletes that user's watches for the affected movies, so removing a movie from the list removes its history.
4. The migration backfills one watch per existing ranking (`watched_at = rated_at`, `rating = rating`, `source = 'manual'`), so no history is lost and nothing is deleted.
5. Switching analytics (activity, streaks) to read `watches`, and any rewatch UI, are out of scope for this ADR and are separate PRD-0008 follow-ups.
6. Rejected alternative: drop `uq_user_movie` and make every `rankings` row a watch. It breaks upsert semantics, delete-by-id, total counts and "already ranked" checks, with a much larger blast radius.

## Consequences
- **Positive**: History is preserved from the moment the write path ships; the change is additive and reversible; the same table later supports notes and per-watch sources.
- **Negative**: Two sources of truth for the current rating until analytics move to `watches` (kept consistent by writing both in one transaction); the backfill must run after the datetime conversion (ADR-0010) and the tmdb_id dedupe so that it copies correct data.
