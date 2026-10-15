---
id: '0021'
title: 'app/models + alembic: reconcile model/migration drift and add `alembic check` to the PostgreSQL CI job'
status: Proposed
governing_adrs:
- ADR-0007
- ADR-0003
governing_prds:
- PRD-0006
governing_stories:
- US-0006
dependencies:
- TASK-0020
target_bc: backend
priority: P2
---

# TASK-0021: app/models + alembic: reconcile model/migration drift and add `alembic check` to the PostgreSQL CI job

## Summary
ADR-0007 requires `alembic check` (models and migrations produce an empty autogenerate diff) in CI, but the two disagree today beyond the datetime types: the `genre_ids` column type and index, and duplicate index declarations on `users` and `oauth_states`. Reconcile them so `alembic check` can be added to the PostgreSQL job and made blocking.

Priority: P2. Size: S. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- `movies.genre_ids`: migration `004_add_movie_metadata.py:44` creates `JSONB` and `:77-84` a GIN index `idx_movies_genre_ids`; the model `app/models/movie.py:58-61` uses generic `JSON` and declares no GIN index. Fix the model with `JSON().with_variant(JSONB(), "postgresql")` (SQLite tests need plain JSON) and declare `Index("idx_movies_genre_ids", "genre_ids", postgresql_using="gin")` in `__table_args__` (it is ignored on SQLite).
- `users.email` and `users.google_id`: the model declares `unique=True` AND `index=True` (`app/models/user.py:36-41` and `:46-51`) AND explicit `Index("idx_users_email", "email")` / `Index("idx_users_google_id", "google_id")` (`:75-76`). The database has a unique constraint on email (`001:51`) plus non-unique `idx_users_email` (`001:55`), and a unique index `idx_users_google_id` (`005:54-58`). Make the model declare each index once, matching the database; if the redundant `idx_users_email` is dropped, do it in a migration with `DROP INDEX IF EXISTS`.
- `oauth_states.state`: model `unique=True, index=True` at `app/models/oauth_state.py:34-39` plus `Index("idx_oauth_states_state", "state")` at `:62`; the database has a single unique index `idx_oauth_states_state` (`005:83-88`). Same fix.
- Procedure: on a scratch PostgreSQL run `alembic upgrade head`, then `alembic revision --autogenerate -m check` and inspect the diff; each entry is either a model fix or a new migration. The final autogenerate diff must be empty. Add `alembic check` as the last step of the TASK-0018 job.

## Notes and Risks
- Prefer changing models over adding migrations; add a migration only for dropping genuinely redundant indexes (write with `IF EXISTS`).
- If `alembic check` reports server-default noise (for example `CURRENT_TIMESTAMP` vs `timezone('utc', now())` from TASK-0020), configure `compare_server_default=False` in `alembic/env.py` (already the default) rather than changing defaults.
- New models from TASK-0025 and TASK-0026 must keep `alembic check` empty; this task establishes the guard.

## Dependencies
- TASK-0020 removes the largest source of drift (datetime types) and owns migration 008; reconciliation migrations must follow it.

## Definition of Done
- [ ] `alembic check` exits 0 on a database built by `alembic upgrade head`.
- [ ] The TASK-0018 job runs `alembic check` as a step and passes.
- [ ] `venv/bin/pytest` still passes on SQLite (the JSON variant keeps SQLite working).
- [ ] Each of `users.email`, `users.google_id` and `oauth_states.state` has exactly one declaration of its index in the model.

```gherkin
Scenario: Model and migration drift fails CI
  Given a pull request that adds a column to a model without a migration
  When the PostgreSQL CI job runs `alembic check`
  Then the job fails and names the missing column
```

## INVEST Criteria
- **Independent**: Ordered after TASK-0020 (see Dependencies); otherwise executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Turns ADR-0007's drift check from aspiration into an enforced gate; PRD-0006 outcome 3, US-0006.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Small: one focused PR, a few files, well under 500 lines of change.
- **Testable**: `alembic check` result in CI against real PostgreSQL (ADR-0007).
