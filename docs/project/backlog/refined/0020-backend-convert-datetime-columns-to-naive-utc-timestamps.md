---
id: '0020'
title: 'alembic + app/models: convert all datetime columns to TIMESTAMP WITHOUT TIME
  ZONE (naive UTC)'
status: Refined
dependencies:
- TASK-0011
- TASK-0018
- TASK-0019
governing_adrs:
- ADR-0010
- ADR-0007
governing_prds:
- PRD-0006
governing_stories:
- US-0007
target_bc: backend
---

# TASK-0020: alembic + app/models: convert all datetime columns to TIMESTAMP WITHOUT TIME ZONE (naive UTC)

## Summary
Migrations 001, 002 and 005 create `timestamptz` columns, while the models, the root `CLAUDE.md` and ADR-0010 say naive UTC `TIMESTAMP WITHOUT TIME ZONE`. The product owner chose to convert the columns to match. Add a reversible migration for all 9 datetime columns, remove the code that works around the mismatch, and correct the docs. Checking the real production column types is a prerequisite step of this task.

Priority: P1. Size: M. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- **Prerequisite (do first, record in the PR description)**: on production run `SELECT table_name, column_name, data_type FROM information_schema.columns WHERE column_name IN ('created_at','updated_at','rated_at','expires_at') AND table_schema = 'public' ORDER BY 1, 2;` and `SHOW timezone;`. Expect `timestamp with time zone` for all 9. Take a backup (`pg_dump`) before running the migration. If a column is already `timestamp without time zone`, the migration must skip it (inspect the type in the migration with `sa.inspect(op.get_bind())` or `information_schema`).
- Columns to convert (migration line references): `users.created_at`, `users.updated_at` (001:40, :46); `movies.created_at`, `movies.updated_at` (001:70, :76); `rankings.created_at`, `rankings.updated_at` (001:105, :111); `rankings.rated_at` (002:30); `oauth_states.created_at`, `oauth_states.expires_at` (005:74, :78). Models: `app/models/user.py:63`, `movie.py:87`, `ranking.py:60`, `oauth_state.py:56-61`.
- New migration `alembic/versions/008_datetime_columns_to_naive_utc.py` (`down_revision` = the id of TASK-0011's migration 007): for each column `op.alter_column(table, col, existing_type=sa.DateTime(timezone=True), type_=sa.DateTime(timezone=False), postgresql_using=f"{col} AT TIME ZONE 'UTC'")`, and set the database default of the columns that have one to `timezone('utc', now())` (`op.alter_column(..., server_default=sa.text("timezone('utc', now())"))`). `downgrade()` reverses with `TYPE timestamptz USING col AT TIME ZONE 'UTC'` and `CURRENT_TIMESTAMP` defaults.
- Models keep `server_default=text("CURRENT_TIMESTAMP")` because SQLite (used by `create_all` in tests) has no `timezone()` function. To make that default UTC on PostgreSQL regardless, set `connect_args={"server_settings": {"timezone": "UTC"}}` on the asyncpg engines in `app/database.py:30-49` (the Lambda `NullPool` and the pooled branch).
- Remove the workaround at `app/routers/google_auth/oauth.py:97-101` (`# Ensure expires_at is naive for comparison (asyncpg may return tz-aware)` and the `replace(tzinfo=None)`), since values are now always naive.
- Docs: root `CLAUDE.md` 'DateTime Handling' is now accurate (leave, but confirm the helper path set by TASK-0014); `app/CLAUDE.md` migration table row 'Timestamps' (line 881, currently 'Existing migrations use `sa.DateTime(timezone=True)` ... match the existing migrations') must now say new migrations use `sa.DateTime()` naive UTC; `app/CLAUDE.md:881` area and any other mention of `timezone=True` likewise.

## Notes and Risks
- `ALTER COLUMN ... TYPE` rewrites the table and takes an `ACCESS EXCLUSIVE` lock for its duration. Tables are small (users, movies, rankings in the low thousands of rows), so expect seconds; still run it when nobody is importing.
- `USING col AT TIME ZONE 'UTC'` converts a `timestamptz` instant to the UTC wall-clock time, so no instant changes meaning. It is correct regardless of the session time zone.
- Deploy order: TASK-0019 must be live before this migration runs in production (otherwise API output briefly loses its offset). Migrations are still applied by hand until TASK-0032 lands; state the order in the PR.
- Day bucketing in analytics (`cast(Ranking.rated_at, Date)`) now follows UTC wall time on every database, which equals today's behavior when the RDS/session time zone is UTC. Rewriting those predicates as range comparisons is optional and not part of this task.
- Another migration touching these tables (TASK-0024, TASK-0025, TASK-0026) should follow this one so new columns copy the convention.

## Dependencies
- TASK-0011 adds migration 007 (head becomes `007_drop_genres_table`); this migration must be 008 with that as `down_revision` to keep a single Alembic head.
- TASK-0018 gives CI a real PostgreSQL run of `alembic upgrade head` and a round trip, which is the only meaningful test of this migration.
- TASK-0019 makes API output UTC-aware so the conversion does not shift times shown in the browser.

## Definition of Done
- [ ] The production column types and `SHOW timezone` output are recorded in the PR description, and a backup was taken.
- [ ] After `alembic upgrade head` on PostgreSQL, a CI step (added to the TASK-0018 job) queries `information_schema.columns` and asserts all 9 columns have `data_type = 'timestamp without time zone'`.
- [ ] `alembic downgrade -1` restores `timestamp with time zone` for all 9 columns and a following `alembic upgrade head` succeeds.
- [ ] On a restored copy of the production backup, `SELECT rated_at AT TIME ZONE 'UTC'` before the migration equals `rated_at` after it for every row of `rankings` (zero differing rows).
- [ ] `app/routers/google_auth/oauth.py` no longer contains the tz-aware workaround and the Google OAuth tests pass.
- [ ] `venv/bin/pytest` passes, and `GET /api/v1/rankings/` still returns `rated_at` with a UTC offset.
- [ ] `app/CLAUDE.md` no longer instructs contributors to use `DateTime(timezone=True)` in new migrations.

```gherkin
Scenario: Timestamps keep their UTC meaning across the conversion
  Given a ranking whose rated_at is 2026-03-01T23:30:00+00:00 before the datetime migration
  When the migration runs and Casey calls GET /api/v1/rankings/
  Then rated_at is returned as 2026-03-01T23:30:00Z
  And the analytics activity endpoint places that ranking on 2026-03-01
```

## INVEST Criteria
- **Independent**: Ordered after TASK-0011, TASK-0018, TASK-0019 (see Dependencies); otherwise executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Makes the schema, models, tests and documentation agree and removes a timezone-dependent behavior; ADR-0010, PRD-0006 outcome 8, US-0007.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Medium: one PR touching several files; keep it under about 500 lines of changed source (excluding generated files and migrations' SQL boilerplate).
- **Testable**: Column types asserted by a CI query on a real PostgreSQL; instant preservation checked on a production-backup copy; API output checked through public endpoints (ADR-0003, ADR-0007).
