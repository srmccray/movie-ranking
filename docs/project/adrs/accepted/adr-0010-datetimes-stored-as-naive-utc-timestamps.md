---
id: ADR-0010
title: Datetimes Are Stored as Naive UTC TIMESTAMP WITHOUT TIME ZONE
status: Accepted
date: '2026-10-14'
---

# ADR-0010: Datetimes Are Stored as Naive UTC TIMESTAMP WITHOUT TIME ZONE

## Status
Accepted

## Context
The root `CLAUDE.md` ("DateTime Handling") states the database uses `TIMESTAMP WITHOUT TIME ZONE` holding naive UTC. The code does not match:
- Migrations 001 (users, movies, rankings), 002 (`rankings.rated_at`) and 005 (`oauth_states.created_at`, `expires_at`) create `sa.DateTime(timezone=True)`, i.e. `timestamptz`. No migration ever converts them, so production columns are almost certainly `timestamptz` (to be confirmed before conversion, see TASK-0020).
- Models declare bare `Mapped[datetime]` (naive). SQLite tests therefore see naive values while production returns timezone-aware ones from asyncpg, and `app/routers/google_auth/oauth.py:97-101` carries a workaround for that.
- Writing a naive datetime into a `timestamptz` column through asyncpg only behaves if the session time zone is UTC; `cast(Ranking.rated_at, Date)` in `app/routers/analytics.py` buckets by the session time zone.
- `datetime.utcnow()` (deprecated since Python 3.12) appears 11 times in `app/`, and `to_naive_utc` is defined twice (`app/routers/rankings.py:26`, `app/routers/import_amazon/review.py:32`).

## Decision
1. **Columns are converted to `TIMESTAMP WITHOUT TIME ZONE`** that store UTC, matching the models and the root `CLAUDE.md`, using `ALTER COLUMN ... TYPE timestamp USING col AT TIME ZONE 'UTC'` for every datetime column (users, movies, rankings x3, oauth_states x2, plus every new table). The migration is reversible (`TYPE timestamptz USING col AT TIME ZONE 'UTC'`). Database-level column defaults become `timezone('utc', now())` and the asyncpg connection sets `timezone=UTC`, so defaults no longer depend on the server's session time zone (the models keep `CURRENT_TIMESTAMP` because SQLite has no `timezone()` function).
2. **The API contract is unchanged: ISO 8601 with an explicit UTC offset.** Because naive datetimes serialize without an offset (and browsers parse an offset-less ISO string as local time), response schemas must serialize datetimes as UTC-aware (`Z` or `+00:00`); this ships before the column conversion (TASK-0019). Request bodies keep accepting any offset and are normalized by one shared `to_naive_utc`.
3. **One helper module**, `app/utils/time.py`, provides `utc_now_naive()` and `to_naive_utc()`. `datetime.utcnow()` and the per-router copies are removed.
4. **Prerequisite, documented in the migration task**: check the real production column types (`\d rankings` and the other tables) and take a database backup before running the migration. If production is already `timestamp without time zone`, the migration is a no-op guarded by a type check.
5. New tables copy the convention: naive UTC columns, defaults via `timezone('utc', now())`.

## Consequences
- **Positive**: Models, migrations, tests and docs agree; SQLite and PostgreSQL behave the same; the `oauth.py` workaround and `AT TIME ZONE` ambiguity disappear; analytics day bucketing no longer depends on the server time zone.
- **Negative**: `ALTER COLUMN TYPE` rewrites tables and takes an `ACCESS EXCLUSIVE` lock (seconds at current data volume); the UTC-aware serialization change (TASK-0019) must be live before the migration runs or the frontend will mis-parse times.
- **Not decided here**: per-user time zones for activity day bucketing (a later product decision).
