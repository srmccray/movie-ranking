---
id: ADR-0007
title: Run Blackbox Tests Against PostgreSQL in CI
status: Accepted
date: '2026-10-14'
amends:
- ADR-0003
---

# ADR-0007: Run Blackbox Tests Against PostgreSQL in CI

## Status
Accepted (amends [`ADR-0003`](adr-0003-blackbox-frontdoor-verification.md))

## Context
ADR-0003 requires tests to go through public entrypoints, but it does not say which database the application runs on while those tests execute. Today every backend test runs on SQLite: `tests/conftest.py` builds a throwaway SQLite file per test, swaps UUID columns for a `SQLiteUUID` type decorator, registers a Python `gen_random_uuid` function, and creates tables with `Base.metadata.create_all`. Production runs PostgreSQL (asyncpg) with a schema built by Alembic migrations 001-006, and **no migration is ever executed in CI**. This hides at least these classes of defect: a migration that fails or drifts from the models (for example `DateTime(timezone=True)` in migrations 001/002/005 versus naive `Mapped[datetime]` in the models, and `JSONB` plus a GIN index in migration 004 versus plain `JSON` in `app/models/movie.py`), PostgreSQL-only behaviour (`gen_random_uuid()` server defaults, check constraints, partial unique indexes, `ALTER COLUMN ... TYPE`), and data migrations that merge rows.

## Decision
Amend ADR-0003 as follows. The blackbox rule itself (public entrypoints only, no private backdoors) is unchanged.

1. **Migrations are part of the system under test.** CI runs a job with a PostgreSQL service container that executes `alembic upgrade head` on an empty database, then `alembic downgrade base` and `alembic upgrade head` again (round trip), then `alembic check` (models and migrations produce no autogenerate diff).
2. **The same blackbox suite runs on PostgreSQL.** CI runs `pytest` a second time with `DATABASE_URL` pointing at the service container and the schema created by Alembic (not `create_all`). SQLite stays the default for local runs and the fast CI job, so contributors keep a quick loop.
3. **Backdoors stay forbidden.** Running SQL directly is still not allowed in feature tests. The only direct database access is schema bootstrap (applying migrations), per-test cleanup, and *migration tests*, which must seed the pre-migration state with SQL because it cannot be created through the API (for example duplicate movies before a dedupe migration). Migration tests live apart from feature tests and say so in their docstrings.
4. **A failure on either database blocks merge** once the PostgreSQL job has been green for one week and is made a required check.

## Consequences
- **Positive**: Migrations, constraints and PostgreSQL-specific SQL are verified before they reach production; later data-model work (datetime conversion, tmdb_id dedupe, import_sessions, watches) can be tested for real.
- **Negative**: One extra CI job (about 2-3 minutes); conftest needs a dialect switch; tests that only passed because of SQLite leniency will surface and need fixing.
- **Follow-up**: TASK-0018 (migration job), TASK-0021 (drift reconciliation so `alembic check` can be required), TASK-0022 (suite on PostgreSQL).
