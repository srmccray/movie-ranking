---
id: '0026'
title: 'app/models/watch.py + alembic: create the watches table and backfill one watch per ranking'
status: Proposed
governing_adrs:
- ADR-0011
- ADR-0010
- ADR-0007
governing_prds:
- PRD-0008
governing_stories:
- US-0011
dependencies:
- TASK-0025
- TASK-0021
target_bc: backend
priority: P2
---

# TASK-0026: app/models/watch.py + alembic: create the watches table and backfill one watch per ranking

## Summary
ADR-0011 stores rewatch history in a new `watches` table while `rankings` keeps the current rating. This task adds only the schema: model, migration, indexes and a backfill that turns each existing ranking into its first watch. No endpoint reads or writes it yet (TASK-0027).

Priority: P2. Size: S. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- Model `app/models/watch.py` (export from `app/models/__init__.py`, which now lists `Movie, OAuthState, Ranking, User` after TASK-0011): `id` UUID PK `server_default=text("gen_random_uuid()")`, `user_id` FK `users.id` ON DELETE CASCADE, `movie_id` FK `movies.id` ON DELETE CASCADE, `watched_at` naive UTC, `rating` integer nullable with `CheckConstraint("rating IS NULL OR (rating >= 1 AND rating <= 5)", name="chk_watch_rating")`, `note` Text nullable, `source` String(50) not null default `'manual'`, `created_at` naive UTC default `CURRENT_TIMESTAMP`. Follow the style of `app/models/ranking.py:37-96` (docstring, `__tablename__`, `__table_args__`).
- Indexes: `idx_watches_user_watched_at (user_id, watched_at DESC)` and `idx_watches_user_movie_watched_at (user_id, movie_id, watched_at DESC)` (the same `desc(...)` pattern as `idx_rankings_user_rated_at`). FK names `fk_watches_user_id`, `fk_watches_movie_id`. No unique constraint on `(user_id, movie_id)`.
- Migration `alembic/versions/011_create_watches_table.py` (`down_revision` = migration 010 from TASK-0025): create the table, then backfill with `INSERT INTO watches (user_id, movie_id, watched_at, rating, source, created_at) SELECT user_id, movie_id, rated_at, rating, 'manual', created_at FROM rankings;` (`gen_random_uuid()` default fills `id`). `downgrade()` drops the table.
- Tests infrastructure: add `Watch` to `patch_uuid_columns` (`tests/conftest.py:83`) and the `before_flush` isinstance check (`:130-135`).
- Migration test in the PostgreSQL CI job (the direct-SQL exception for migration tests in ADR-0007 clause 3): `alembic upgrade 010`, insert users, movies and N rankings, `alembic upgrade head`, assert `count(*)` of `watches` equals N and each `watched_at` equals the ranking's `rated_at`.

## Notes and Risks
- Additive and reversible: nothing reads the table yet, so a rollback of the code needs no data fix.
- Backfill uses `rated_at` rather than `created_at` as the watch date because `rated_at` is what the UI shows as the date watched.
- Keep user-visible behavior unchanged; analytics keep reading `rankings` (PRD-0008 non-goal).

## Dependencies
- TASK-0025: owns migration 010; this is 011 and must follow it to keep a single Alembic head.
- TASK-0021: the model and migration for the new table must keep `alembic check` empty, so the guard has to exist first.

## Definition of Done
- [ ] `alembic upgrade head` creates `watches` with the two indexes and `chk_watch_rating`; `alembic downgrade -1` drops it; `alembic check` is empty.
- [ ] After migration, `SELECT count(*) FROM watches` equals `SELECT count(*) FROM rankings`, and no watch has `watched_at` different from its ranking's `rated_at` (migration test).
- [ ] `venv/bin/pytest` passes on SQLite and PostgreSQL with the new model registered in the test fixtures.

```gherkin
Scenario: Existing rankings become first watches
  Given Casey has 120 rankings before the watches migration
  When the migration completes
  Then Casey has 120 watches, each dated with its ranking's rated_at
```

## INVEST Criteria
- **Independent**: Ordered after TASK-0025, TASK-0021 (see Dependencies); otherwise executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Lays the data foundation for rewatch history without changing behavior; ADR-0011, PRD-0008 outcome 1, US-0011.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Small: one focused PR, a few files, well under 500 lines of change.
- **Testable**: Migration test on PostgreSQL asserting counts and dates (ADR-0007); no API change in this task.
