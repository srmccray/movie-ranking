---
id: '0008'
title: Rewatch History
status: Shaped
created: 2026-10-14
target_persona: Casey (The Movie Enthusiast)
component: backend
---

# PRD-0008 — Rewatch History

## Who this is for

- **Casey (The Movie Enthusiast)**: watches favourites more than once, re-rates them, and imports watch history that includes repeat viewings.

## What the person cannot do today

- Record a second viewing. `rankings` allows one row per user and movie (`uq_user_movie`), and both write paths overwrite it: `POST /api/v1/rankings/` replaces `rating` (and `rated_at` when sent), and the import `add` endpoint replaces `rating` and `rated_at` unconditionally (`app/routers/import_amazon/review.py:196-211`). Casey's earlier rating and watch date are lost, and activity and streak analytics only know the most recent date.

## What good looks like

1. **History is never overwritten**: when Casey records a rewatch (explicitly, or by importing a repeat viewing) a new watch is saved with its own date and rating and the ranking shows the newest one; the earlier watches stay. Correcting a rating or date with the existing edit controls changes the current watch and is not a rewatch.
2. **Nothing changes for current screens**: rankings list, search, import and analytics responses keep their shapes (ADR-0011: additive `watches` table, `rankings` unchanged in meaning).
3. **Existing data is preserved**: each existing ranking becomes the first watch of that movie.

## What this does not do

- No rewatch UI, no per-watch notes UI, no change to analytics (activity and streak queries still read `rankings.rated_at`); each is a follow-up PRD once the data exists.
- No change to the 1-5 rating scale.
- No deletion semantics for individual watches other than removing a movie's watches together with its ranking (and cascading with the user or movie).

## Checkable Outcomes

1. After the migration, `SELECT count(*) FROM watches` equals `SELECT count(*) FROM rankings` and every watch has `watched_at = rated_at` of its ranking.
2. Rating a movie 5 on 2025-01-10 and then recording a rewatch with rating 3 on 2026-02-01 through `POST /api/v1/rankings/{id}/watches/` leaves `GET /api/v1/rankings/` showing rating 3 and `GET /api/v1/rankings/{id}/watches/` returning two watches, with ratings 3 and 5 in newest-first order.
3. Adding a movie through the Amazon import for a title the user already ranked appends a watch dated with the CSV watch date and does not change the earlier watch's rating or date.
4. `GET /api/v1/rankings/{id}/watches/` for another user's ranking returns 403 and for an unknown id returns 404.
5. Deleting a ranking via `DELETE /api/v1/rankings/{id}/` removes that movie's watches for that user.
6. All previously passing backend tests pass without edits to their assertions.

## Linked User Stories

- [US-0011: Rate a rewatch without losing earlier ratings](../../user_stories/accepted/us-0011-rate-a-rewatch-without-losing-earlier-ratings.md)

## Implementing Backlog Tasks

- TASK-0026 (watches table, migration and backfill)
- TASK-0027 (rewatch endpoint, import write path and read endpoint)

## Refinement Notes

- Governing decision: ADR-0011. Depends on ADR-0010 (datetime convention) and on movie identity cleanup (TASK-0023, TASK-0024) so the backfill copies clean data.
- Open product question for Jordan: should an import of an already-ranked title append a watch (this PRD's default) or ask the user? The default avoids data loss without adding a prompt.
- Design assumption to confirm: the existing `POST /rankings/` upsert is kept as a *correction* (the inline rating and date edit in the UI calls it), so a rewatch needs the new explicit endpoint; a UI to record rewatches is a follow-up PRD.
