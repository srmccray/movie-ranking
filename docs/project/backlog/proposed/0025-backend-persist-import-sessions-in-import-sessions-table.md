---
id: '0025'
title: 'app/services/import_session.py + alembic: persist import sessions in an import_sessions table'
status: Proposed
governing_adrs:
- ADR-0010
- ADR-0007
- ADR-0003
governing_prds:
- PRD-0006
governing_stories:
- US-0008
dependencies:
- TASK-0020
- TASK-0017
- TASK-0024
target_bc: backend
priority: P1
---

# TASK-0025: app/services/import_session.py + alembic: persist import sessions in an import_sessions table

## Summary
Import sessions live in a process-global dict (`ImportSessionStore`, `app/services/import_session.py:48-257`, singleton at line 257). The API runs on AWS Lambda behind API Gateway (`infra/lib/movie-ranking-stack.ts`), where concurrent requests can hit different containers and idle containers are recycled. Any miss yields `404 Import session not found or expired` in the middle of reviewing up to 500 titles. Persist sessions in PostgreSQL behind the same behavior. This also unblocks Import v2 (bulk add and persisted unmatched items).

Priority: P1. Size: M. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- Current API: `create_session(user_id, movies, total_entries, movies_found, tv_shows_filtered, already_ranked) -> str` (line 89), `get_session(session_id, user_id)` (143), `update_session` (176), `delete_session` (213), `cleanup_expired` (227), `get_session_count` (247). Rules to keep: one active session per user (a new upload replaces the old one), 30-minute TTL (`SESSION_TTL_MINUTES = 30`), at most 500 movies (`MAX_MOVIES_PER_SESSION`), ownership enforced on every read. `ImportSession` fields: `user_id`, `movies` (list of dicts), `created_at`, `current_index`, `added_count`, `skipped_count`, `total_entries`, `movies_found`, `tv_shows_filtered`, `already_ranked`.
- Callers (all in `app/routers/import_amazon/`): `session.py:92` (create), `:138` and `:183` (get, delete), and via the helper from TASK-0017 in `review.py` (add, skip, match). Handlers mutate the session in place after the DB work (`review.py:224-226`: `session.movies[index]["status"] = "added"`, `added_count += 1`, `current_index = index + 1`; skip and match are similar), so persistence must happen explicitly (a `save` call) or through tracked mutable JSON.
- New model `app/models/import_session.py` and migration `alembic/versions/010_create_import_sessions_table.py`: `id` UUID PK (`gen_random_uuid()`), `user_id` UUID FK `users.id` ON DELETE CASCADE with a **unique** constraint (one session per user), `movies` JSON (use `JSON().with_variant(JSONB(), "postgresql")` so SQLite tests work), `current_index`, `added_count`, `skipped_count`, `total_entries`, `movies_found`, `tv_shows_filtered`, `already_ranked` (integers, default 0), `created_at`, `expires_at` (naive UTC, ADR-0010), index `idx_import_sessions_expires_at`. Name FK `fk_import_sessions_user_id`, unique `uq_import_sessions_user_id`.
- Rewrite the store as async methods taking `db: AsyncSession` (`create_session` replaces any existing row for the user in one transaction; `get_session` returns `None` when missing, owned by someone else or `expires_at` passed; mutating handlers load with `with_for_update()` so two concurrent add/skip calls serialize on PostgreSQL). Purge expired rows opportunistically on create (the pattern used for `oauth_states` in `app/routers/google_auth/oauth.py`). Keep `MAX_MOVIES_PER_SESSION` enforcement.
- Tests: `tests/test_import_session_create.py` and `tests/test_import_session_access.py` instantiate `ImportSessionStore` directly and call its synchronous methods; port them to the async API (or, preferably, to endpoint-level tests) with the same coverage. Add the new model to `patch_uuid_columns` (`tests/conftest.py:83`) and the `before_flush` listener (`:130-135`) so SQLite mode works.

## Notes and Risks
- Behavior to preserve: user B cannot read user A's session (404, not 403); a new upload replaces the old session; 404 after 30 minutes.
- Persisting is the reason `expires_at` exists: do not rely on `created_at + TTL` computed in Python only.
- A session row holds up to 500 movie dicts (well under 1 MB of JSON), so TOAST storage is fine. DynamoDB with TTL was considered and rejected (extra service and IAM).
- Restart test for the Definition of Done: create the session through `POST .../upload/`, build a second app/engine instance over the same database (or restart the process in the PostgreSQL CI job) and fetch the session.

## Dependencies
- TASK-0020: the new table's timestamps must follow the naive-UTC convention (ADR-0010) and migration numbering continues from 008/009.
- TASK-0017: all handlers fetch sessions through one helper, so the lookup changes in one place.
- TASK-0024: owns migration 009; this is 010 and must follow it to avoid multiple Alembic heads.

## Definition of Done
- [ ] Migration 010 creates `import_sessions` with the unique `user_id` constraint and `expires_at` index; `alembic upgrade head`, `downgrade -1` and `alembic check` pass in CI.
- [ ] No module-level in-memory session dictionary remains in `app/services/import_session.py`.
- [ ] After upload and adding 3 movies, a new application instance over the same database returns the session with 3 movies marked `added` and the same `current_index`.
- [ ] A session older than 30 minutes returns 404 `Import session not found or expired`, and another user's session id returns 404.
- [ ] Two concurrent `add` requests for different indexes on one session both persist (counters equal 2) on PostgreSQL.
- [ ] Existing import tests pass (ported where they used the store class directly) with no loss of coverage; `app/CLAUDE.md:792` no longer says sessions are lost on restart.

```gherkin
Scenario: Review continues after the server restarts
  Given Casey uploaded an Amazon Prime CSV and added 3 movies from the review list
  When the backend process restarts
  And Casey requests the same import session
  Then the session is returned with 3 movies marked "added" and the current index unchanged
```

## INVEST Criteria
- **Independent**: Ordered after TASK-0020, TASK-0017, TASK-0024 (see Dependencies); otherwise executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Removes the most likely functional bug in production (random 404s mid-import) and unblocks Import v2; PRD-0006 outcome 9, US-0008.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Medium: one PR touching several files; keep it under about 500 lines of changed source (excluding generated files and migrations' SQL boilerplate).
- **Testable**: Observable through the public import endpoints with a restarted app instance (ADR-0003); migration verified on PostgreSQL (ADR-0007).
