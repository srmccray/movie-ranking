---
id: '0006'
title: Platform Foundations
status: Accepted
created: 2026-10-14
target_persona: Alex (The Systems Builder)
component: core
---

# PRD-0006 — Platform Foundations

## Who this is for

- **Alex (The Systems Builder)**: maintains movie-ranking with AI coding agents and needs CI, the data model and the code to be trustworthy enough that agents can change them without silent regressions.
- **Casey (The Movie Enthusiast)**: benefits indirectly; the import review stops failing with "Import session not found or expired" and no two rows exist for the same film.

## What the person cannot do today

- **Trust CI.** The frontend job deliberately skips eslint and `tsc -b` (`.github/workflows/ci.yml:87`) because they fail today (7 eslint errors and 2 warnings, 70 TypeScript errors). Backend tests run only on SQLite, so Alembic migrations 001-006 are never executed and the models have drifted from them (timestamp types, `JSONB`, duplicate indexes). MSW logs unhandled requests as warnings, so tests can call endpoints that have no mock.
- **Trust the stored data.** `movies.tmdb_id` is not unique and `POST /api/v1/movies/` always inserts, so one film can exist many times; timestamps are `timestamptz` in migrations but documented and modelled as naive UTC; import sessions live in Lambda process memory (`app/services/import_session.py`), so concurrent or recycled containers produce 404s mid-review.
- **Change code safely.** Dead code (`Genre` model and table, `ImportCompletionResponse`, `VITE_API_BASE_URL`), 11 `datetime.utcnow()` calls, duplicated helpers (`to_naive_utc` twice, genre aggregation twice in `analytics.py`, session and index checks repeated in the import routers) and a CSS token that is used but never defined (`--color-primary-400`) make edits risky. Frontend API types are copied by hand from the backend schemas.

## What good looks like

1. **Enforced gates**: pull requests run eslint, `tsc -b`, the frontend tests, the backend suite on SQLite and on PostgreSQL (with Alembic migrations applied from scratch and no model/migration drift), and an OpenAPI/TypeScript drift check.
2. **One truth for data**: movies are unique by TMDB id, datetime columns match the documented naive-UTC convention (ADR-0010), and import sessions persist in the database (US-0008).
3. **Clean code base**: dead code removed, helpers shared, `analytics.py` back under the 400-line warning threshold, every API call in frontend tests has an explicit handler.

## What this does not do

- No new end-user features (rewatch history is PRD-0008; import v2, UI refresh and BDD expansion are later waves).
- No change to API paths, status codes or response shapes, other than `POST /api/v1/movies/` returning the existing movie (HTTP 200) when the TMDB id already exists.
- No service-layer rewrite (a layering ADR is deferred until the shared helpers land), no TanStack Query adoption.

## Checkable Outcomes

1. `npm run lint` and `npx tsc -b` in `frontend/` both exit 0, and `.github/workflows/ci.yml` runs both on every pull request.
2. With an MSW handler missing, a frontend test that calls that endpoint fails (`onUnhandledRequest: 'error'`), and the full `npm run test:run` still passes.
3. A CI job with a PostgreSQL service container runs `alembic upgrade head`, `alembic downgrade base`, `alembic upgrade head` and `alembic check`, and all four exit 0.
4. `pytest` passes against PostgreSQL in CI with the schema created by Alembic.
5. `grep -rn "utcnow" app/` returns nothing, and `grep -rn "Genre\b" app/models/` returns nothing.
6. `wc -l app/routers/analytics.py` reports fewer than 400 lines and `tests/test_analytics.py` passes with an unchanged test count.
7. Posting the same `tmdb_id` twice to `POST /api/v1/movies/` returns the same movie `id` (201 then 200), and `SELECT tmdb_id FROM movies WHERE tmdb_id IS NOT NULL GROUP BY tmdb_id HAVING count(*) > 1` returns no rows after the dedupe migration.
8. `SELECT data_type FROM information_schema.columns WHERE table_name = 'rankings' AND column_name = 'rated_at'` returns `timestamp without time zone`, and `GET /api/v1/rankings/` still returns `rated_at` with a UTC offset.
9. After uploading an Amazon Prime CSV, restarting the backend process and then calling `GET /api/v1/import/amazon-prime/session/{id}/` returns the session instead of 404.
10. Changing a field in a Pydantic response schema without regenerating `frontend/src/api/schema.d.ts` fails the CI drift check.

## Linked User Stories

- [US-0006: Catch regressions in CI before merge](../../user_stories/accepted/us-0006-catch-regressions-in-ci-before-merge.md)
- [US-0007: Keep code and stored data consistent](../../user_stories/accepted/us-0007-keep-code-and-stored-data-consistent.md)
- [US-0008: Resume an import review without losing progress](../../user_stories/accepted/us-0008-resume-an-import-review-without-losing-progress.md)

## Implementing Backlog Tasks

- TASK-0008, TASK-0009, TASK-0010 (frontend lint, type and mock gates)
- TASK-0011, TASK-0012, TASK-0013 (dead code and the missing CSS token)
- TASK-0014, TASK-0015, TASK-0016, TASK-0017 (backend duplication and cheap fixes)
- TASK-0018, TASK-0021, TASK-0022 (PostgreSQL in CI, ADR-0007)
- TASK-0019, TASK-0020 (UTC-aware responses, datetime column conversion, ADR-0010)
- TASK-0023, TASK-0024 (movie identity: get-or-create, dedupe and unique index)
- TASK-0025 (import sessions persisted in the database)
- TASK-0042, TASK-0043, TASK-0044 (OpenAPI generated types, ADR-0012)
