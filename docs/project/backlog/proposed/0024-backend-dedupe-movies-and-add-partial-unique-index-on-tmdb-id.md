---
id: '0024'
title: 'alembic + app/models/movie.py: merge duplicate movies by tmdb_id and add a partial unique index'
status: Proposed
governing_adrs:
- ADR-0010
- ADR-0007
- ADR-0003
governing_prds:
- PRD-0006
governing_stories:
- US-0007
dependencies:
- TASK-0023
- TASK-0020
target_bc: backend
priority: P1
---

# TASK-0024: alembic + app/models/movie.py: merge duplicate movies by tmdb_id and add a partial unique index

## Summary
`movies.tmdb_id` is nullable with a non-unique index (`app/models/movie.py:48-51`, `:105`; migration 003). Existing duplicates must be merged without losing rankings, then the database must refuse new ones. Write a data-merging migration, add `UNIQUE (tmdb_id) WHERE tmdb_id IS NOT NULL`, and harden the get-or-create helper against races.

Priority: P1. Size: M. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- **Preflight on production (record the result in the PR)**: `SELECT tmdb_id, count(*) AS n FROM movies WHERE tmdb_id IS NOT NULL GROUP BY tmdb_id HAVING count(*) > 1 ORDER BY n DESC;` and the number of affected rankings. Take a backup first.
- Migration `alembic/versions/009_dedupe_movies_add_unique_tmdb_id.py` (`down_revision` = migration 008 from TASK-0020). For each duplicate group keep the oldest row as canonical (`ORDER BY created_at, id`). Back-fill the canonical row's NULL metadata from the duplicates (`COALESCE`). Re-point rankings: if the user already has a ranking on the canonical movie, keep the one with the latest `rated_at` (copy its `rating` and `rated_at` onto the canonical ranking row if it is the newer one) and delete the other; otherwise `UPDATE rankings SET movie_id = canonical`. Then `DELETE FROM movies` for the duplicate ids (`rankings.movie_id` is `ON DELETE CASCADE`, so re-point before deleting).
- Then create the index: `op.create_index("uq_movies_tmdb_id", "movies", ["tmdb_id"], unique=True, postgresql_where=sa.text("tmdb_id IS NOT NULL"))` and drop the old non-unique `idx_movies_tmdb_id` (`003_add_tmdb_fields.py:39`). `downgrade()` drops the unique index and recreates the non-unique one (merged rows are not restored; say so in the docstring).
- Model: `app/models/movie.py:105` `Index("idx_movies_tmdb_id", "tmdb_id")` becomes `Index("uq_movies_tmdb_id", "tmdb_id", unique=True, postgresql_where=text("tmdb_id IS NOT NULL"), sqlite_where=text("tmdb_id IS NOT NULL"))` so SQLite tests enforce it too.
- Helper: in `app/services/movies.py` (TASK-0023) wrap the insert in `async with db.begin_nested():` and on `IntegrityError` re-select the existing row and return it as the 'already existed' result.
- Migration test (the one place ADR-0007 clause 3 allows direct SQL, because the pre-migration state cannot be created through the API): in the PostgreSQL CI job, `alembic upgrade 008`, insert two users, three movies sharing a `tmdb_id` and rankings that overlap, `alembic upgrade 009`, assert one movie row remains, rankings were merged to the latest `rated_at`, and a second insert with the same `tmdb_id` fails. Mark the test clearly as a migration test.

## Notes and Risks
- This is a data-destroying migration (it deletes rows). The backup and the preflight query are mandatory; do not run it without them.
- Watches do not exist yet (TASK-0026 comes later), so there is nothing else to re-point.
- `matching.py` and `review.py` already treat `tmdb_id` as the identity; they need no change beyond using the helper.
- `idx_movies_tmdb_id` exists in `alembic check` terms; coordinate with TASK-0021 so the final model/migration diff stays empty.

## Dependencies
- TASK-0023 stops new duplicates and introduces the shared helper that this task hardens with an `IntegrityError` retry.
- TASK-0020 owns migration 008; this migration is 009 with it as `down_revision`.

## Definition of Done
- [ ] The preflight duplicate query result and the backup confirmation are in the PR description.
- [ ] After the migration, `SELECT tmdb_id FROM movies WHERE tmdb_id IS NOT NULL GROUP BY tmdb_id HAVING count(*) > 1` returns no rows, and the total number of `(user_id, movie_id)` pairs in `rankings` has not increased.
- [ ] A migration test (PostgreSQL job) proves ranking merge by latest `rated_at` and the unique violation on a repeated `tmdb_id`.
- [ ] Two simultaneous `POST /api/v1/movies/` requests with the same `tmdb_id` (a test using `asyncio.gather`) return the same movie `id` and create one row.
- [ ] `alembic downgrade -1` and `alembic upgrade head` succeed; `venv/bin/pytest` passes on SQLite and PostgreSQL.

```gherkin
Scenario: Duplicate films are merged without losing rankings
  Given movies A and B share TMDB id 603, user U ranked A with 3 on 2025-01-01 and B with 5 on 2026-01-01
  When migration 009 runs
  Then one movie with TMDB id 603 remains
  And U has one ranking for it with rating 5 and rated_at 2026-01-01
  And inserting another movie with TMDB id 603 is rejected
```

## INVEST Criteria
- **Independent**: Ordered after TASK-0023, TASK-0020 (see Dependencies); otherwise executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Restores movie identity so rankings, analytics and later watches reference one row per film; PRD-0006 outcome 7, US-0007.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Medium: one PR touching several files; keep it under about 500 lines of changed source (excluding generated files and migrations' SQL boilerplate).
- **Testable**: Migration verified on real PostgreSQL in CI plus public-endpoint concurrency test (ADR-0003, ADR-0007).
