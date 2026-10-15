---
id: '0027'
title: 'app/routers/rankings.py + import_amazon/review.py: record watches on rewatch and import, add GET/POST /rankings/{id}/watches/'
status: Proposed
governing_adrs:
- ADR-0011
- ADR-0003
governing_prds:
- PRD-0008
governing_stories:
- US-0011
dependencies:
- TASK-0026
- TASK-0023
- TASK-0015
target_bc: backend
priority: P2
---

# TASK-0027: app/routers/rankings.py + import_amazon/review.py: record watches on rewatch and import, add GET/POST /rankings/{id}/watches/

## Summary
With the `watches` table in place, make rewatches stop overwriting history. The existing upsert `POST /api/v1/rankings/` keeps its current meaning of correcting the current rating or date (the frontend edit controls call it: `useRankings.updateRating` and `updateRatedAt` go through `createOrUpdateRanking`), so rewatches get an explicit endpoint, and the Amazon import appends a watch when the title is already ranked.

Priority: P2. Size: M. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- **Create path** (`app/routers/rankings.py:84-115` new ranking branch and `:109` `rated_at`): also insert the first `Watch` (`watched_at = rated_at`, `rating`, `source='manual'`) in the same transaction.
- **Correction path** (`rankings.py:96-107`, existing ranking branch): keep updating the ranking, and also update the newest watch of that `(user, movie)` (`rating`, and `watched_at` when `rated_at` is sent) so the two agree. This is a correction, not a rewatch.
- **New `POST /api/v1/rankings/{ranking_id}/watches/`** (201, request `WatchCreate`: `rating` 1-5, optional `watched_at` defaulting to now via `utc_now_naive()`, optional `note`): ownership as in `delete_ranking` (403 for another user's ranking, 404 unknown id, per `rankings.py:255-292`), appends a watch (`source='manual'`), then sets the ranking's `rating`/`rated_at` from the watch with the greatest `watched_at` (ties: latest `created_at`). Back-dated watches therefore do not replace a newer current rating. Returns the new watch.
- **New `GET /api/v1/rankings/{ranking_id}/watches/`** returns `WatchListResponse` (`items: list[WatchResponse]`, newest first; `WatchResponse` uses `UTCDatetime` from TASK-0019). Add schemas in `app/schemas/watch.py` and a router module `app/routers/rankings_watches.py` (or a package) included in `app/main.py` and `tests/conftest.py`; `rankings.py` is 292 lines and must stay under 400 (ADR-0002).
- **Import path** (`app/routers/import_amazon/review.py:195-221`): when the user already has a ranking for the movie, append a `Watch` (`source='amazon_prime'`, `watched_at` = the computed `rated_at`, `rating` = request rating) and update the ranking from the newest watch instead of unconditionally overwriting `rating` and `rated_at`. New ranking: create it plus its first watch.
- **Deletion**: `delete_ranking` (`rankings.py:255-292`) and `delete_all_rankings` also delete the user's watches for the affected movies (ADR-0011 clause 3).
- Docs: endpoint tables in `app/CLAUDE.md`; frontend types are untouched (no UI in this task); mention the new routes for the OpenAPI export (TASK-0042).

## Notes and Risks
- Why not make `POST /rankings/` always append? The UI's inline edit of rating and date uses it, so every edit would fabricate a rewatch. Flagged as a product assumption in PRD-0008 Refinement Notes; Jordan may prefer a different split.
- Responses of existing endpoints do not change.
- Trailing slashes on both new routes (project convention); status codes follow the root `CLAUDE.md` table (201 create, 200 read, 403/404).
- Run the full suite on PostgreSQL (TASK-0022) because the 'newest watch' ordering must behave identically on both databases.

## Dependencies
- TASK-0026 provides the table and model.
- TASK-0023: `review.py`'s movie get-or-create block is moved by that task; this one edits the ranking upsert below it.
- TASK-0015 rewrites `delete_all_rankings`, which this task must extend to delete watches.

## Definition of Done
- [ ] Creating a ranking creates one watch; correcting the rating through `POST /api/v1/rankings/` does not add a watch and the newest watch reflects the corrected values.
- [ ] `POST /api/v1/rankings/{id}/watches/` with rating 3 on 2026-02-01 after an initial rating 5 on 2025-01-10 leaves `GET /api/v1/rankings/` showing rating 3, and `GET /api/v1/rankings/{id}/watches/` returns both watches newest first.
- [ ] A watch back-dated before the newest existing watch is stored but does not change the ranking's current rating.
- [ ] Adding an already-ranked title through the Amazon import appends a watch with the CSV date and leaves the earlier watch's rating and date unchanged.
- [ ] Another user's ranking returns 403 and an unknown id 404 on both new endpoints; deleting a ranking removes its watches.
- [ ] All previously passing backend tests pass without edits to their assertions; new files are under 400 lines.

```gherkin
Scenario: A second rating keeps the first
  Given Casey rated "Heat" 5 on 2025-01-10
  When Casey records a rewatch of "Heat" with rating 3 on 2026-02-01
  Then the rankings list shows "Heat" with rating 3
  And the watch history of that ranking lists the 2026-02-01 watch with rating 3 and the 2025-01-10 watch with rating 5
```

## INVEST Criteria
- **Independent**: Ordered after TASK-0026, TASK-0023, TASK-0015 (see Dependencies); otherwise executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Delivers the product decision that rewatches must not overwrite old ratings; ADR-0011, PRD-0008 outcomes 2-5, US-0011.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Medium: one PR touching several files; keep it under about 500 lines of changed source (excluding generated files and migrations' SQL boilerplate).
- **Testable**: Observable through the public rankings, watches and import endpoints (ADR-0003).
