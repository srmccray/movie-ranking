---
id: '0022'
title: 'tests/conftest.py + ci.yml: run the blackbox pytest suite against PostgreSQL with Alembic-built schema'
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
- TASK-0021
target_bc: backend
priority: P2
---

# TASK-0022: tests/conftest.py + ci.yml: run the blackbox pytest suite against PostgreSQL with Alembic-built schema

## Summary
Every backend test runs on a throwaway SQLite database with UUID and `gen_random_uuid` shims (`tests/conftest.py:77-189`). ADR-0007 requires the same suite to run on PostgreSQL with the schema built by Alembic. Add a dialect switch to the `client` fixture and a CI step that runs the suite against the service container from TASK-0018.

Priority: P2. Size: M. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- `tests/conftest.py`: the `client` fixture (line 96) calls `patch_uuid_columns()` (line 77-93, mutates model column types to `SQLiteUUID` for the whole process), creates a temp SQLite file engine (`create_async_engine` at line 111), registers `gen_random_uuid` on connect (line 121-123), assigns UUIDs in a `before_flush` listener (line 127) and runs `Base.metadata.create_all` (line 149).
- Add `TEST_DATABASE_URL`: when it starts with `postgresql`, (a) do NOT call `patch_uuid_columns()`, (b) create the engine from the URL with `poolclass=NullPool`, (c) skip the SQLite function registration and `create_all` (the schema already exists from `alembic upgrade head`), (d) before each test run `TRUNCATE users, movies, rankings, oauth_states, ... RESTART IDENTITY CASCADE` through the engine (cleanup is the only direct SQL allowed by ADR-0007 clause 3). Keep the SQLite path unchanged when the variable is unset. Because the models are shared across tests in one process, choose the mode once at import time.
- `ci.yml`: in the `backend-postgres` job from TASK-0018, after the migration steps, `pip install pytest pytest-asyncio httpx aiosqlite` and run `pytest` with `TEST_DATABASE_URL` set.
- Tests mention the divergence directly at `tests/test_analytics.py:41` (comment about PostgreSQL vs SQLite); revisit it once the suite runs on both.

## Notes and Risks
- Expect a first wave of PostgreSQL-only failures (case-sensitive text comparison, ordering without `ORDER BY`, check constraints, stricter type binding). Fix tests or application code as appropriate; never weaken assertions to pass.
- Keep the SQLite run as the fast default and in the existing `preflight-and-invariants` job.
- Models added later (TASK-0025, TASK-0026) must be added to the lists in `patch_uuid_columns` (line 83) and in the `before_flush` listener (line 130-135) for the SQLite mode; note this in the PR description of those tasks.
- After one week green, make the job a required check (ADR-0007 clause 4); that is a repository setting, not a code change.

## Dependencies
- TASK-0020: until columns are `timestamp without time zone`, naive datetimes written by the app mismatch `timestamptz` columns and many tests would fail for a known reason.
- TASK-0021: the schema built from migrations must equal the model schema for the suite to be meaningful.

## Definition of Done
- [ ] With `TEST_DATABASE_URL` unset, `venv/bin/pytest` behaves exactly as before (same collected and passed counts).
- [ ] With `TEST_DATABASE_URL` pointing at a PostgreSQL database migrated to head, `pytest` passes in CI in the `backend-postgres` job.
- [ ] The suite on PostgreSQL does not call `Base.metadata.create_all`.
- [ ] The CI job fails when a test is broken only on PostgreSQL (demonstrated in the PR by one deliberate PostgreSQL-only failure that is then reverted).

```gherkin
Scenario: The blackbox suite passes on PostgreSQL
  Given a PostgreSQL database built with `alembic upgrade head`
  When `pytest` runs with TEST_DATABASE_URL set
  Then every test that passes on SQLite also passes
  And no test creates tables with create_all
```

## INVEST Criteria
- **Independent**: Ordered after TASK-0020, TASK-0021 (see Dependencies); otherwise executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Closes the SQLite/PostgreSQL blind spot for every future data-model change; ADR-0007, PRD-0006 outcome 4, US-0006.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Medium: one PR touching several files; keep it under about 500 lines of changed source (excluding generated files and migrations' SQL boilerplate).
- **Testable**: The suite itself is the verification; the CI result against a real PostgreSQL service is the observable (ADR-0003, ADR-0007).
