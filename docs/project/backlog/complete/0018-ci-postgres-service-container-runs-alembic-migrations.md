---
id: 0018
title: 'ci.yml: add a PostgreSQL job that runs alembic upgrade head and a downgrade/upgrade
  round trip'
status: Complete
dependencies:
- TASK-0009
governing_adrs:
- ADR-0003
- ADR-0007
governing_prds:
- PRD-0006
governing_stories:
- US-0006
target_bc: infra
---

# TASK-0018: ci.yml: add a PostgreSQL job that runs alembic upgrade head and a downgrade/upgrade round trip

## Summary
Alembic migrations 001-006 have never been executed in CI: backend tests use `Base.metadata.create_all` on SQLite (`tests/conftest.py:149`). ADR-0007 (amending ADR-0003) makes migrations part of the system under test. Add a CI job with a PostgreSQL service container that applies every migration from an empty database and proves the downgrade path.

Priority: P1. Size: S. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- `.github/workflows/ci.yml` currently has two jobs: `preflight-and-invariants` (SpecOps health + `pytest` on SQLite, Python 3.13) and `frontend-tests`. Add a third job `backend-postgres` named `Backend Migrations (PostgreSQL)`.
- Service: `postgres:16` with `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` set, port 5432 published, and `options: --health-cmd "pg_isready -U ..." --health-interval 5s --health-retries 10`.
- Python: use 3.12 (the Lambda runtime in `deploy.yml` `PYTHON_VERSION` and the `Dockerfile` base image), not 3.13, so migrations run on the production interpreter. `pip install -r requirements.txt`.
- Environment for every step: `DATABASE_URL=postgresql+asyncpg://<user>:<pw>@localhost:5432/<db>` plus dummy `SECRET_KEY` and `TMDB_API_KEY` (`app/config.py` declares `DATABASE_URL`, `SECRET_KEY`, `TMDB_API_KEY` without defaults and `alembic/env.py:24` loads `settings`, so alembic fails without them).
- Steps: `alembic upgrade head`; `alembic downgrade base`; `alembic upgrade head`; then a small script step asserting expected objects exist (for example the `rankings` table and the `uq_user_movie` constraint via `psql` or `python -c`). Do not add `alembic check` here: the models and migrations currently drift (TASK-0021 fixes that and adds the step).
- Run on every pull request and push to `main` (no path filter, like `frontend-tests`) so the check always reports and can later be required (ADR-0007 clause 4).

## Notes and Risks
- This is the first time migrations run anywhere automated. Expect the job to find real defects (a broken `downgrade()`, PostgreSQL-only syntax). Fix the smallest thing that makes the round trip pass; editing an already-applied migration's `downgrade()` is safe, editing an `upgrade()` that has run in production is not (add a new migration instead).
- Migration 001 creates `gen_random_uuid()` defaults, which need PostgreSQL 13+ built in or the `pgcrypto` extension; `postgres:16` has it built in. Check what production runs and note it in `infra/CLAUDE.md` if it differs.
- Keep the job independent of the SQLite `pytest` run; running the suite on PostgreSQL is TASK-0022.

## Dependencies
- TASK-0009 also edits `.github/workflows/ci.yml`; doing this second avoids a merge conflict in the same file.

## Definition of Done
- [ ] `ci.yml` has a PostgreSQL service job that passes on `main` with `alembic upgrade head`, `alembic downgrade base` and `alembic upgrade head` all exiting 0.
- [ ] A pull request containing a migration with invalid SQL fails this job at `alembic upgrade head`.
- [ ] The job's Python version matches the Lambda runtime (3.12) and the job runs without any path filter.
- [ ] `spec-ops health --numbering` and `spec-ops health` still pass.

```gherkin
Scenario: Migrations are exercised on PostgreSQL
  Given a pull request that adds an Alembic migration with invalid SQL
  When the CI Quality Gate workflow runs
  Then the PostgreSQL job fails at `alembic upgrade head`
  And the pull request cannot merge
```

## INVEST Criteria
- **Independent**: Ordered after TASK-0009 (see Dependencies); otherwise executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: First automated proof that the schema production runs on can actually be built from migrations; ADR-0007, PRD-0006 outcome 3, US-0006.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Small: one focused PR, a few files, well under 500 lines of change.
- **Testable**: Observable as a CI job result against a real PostgreSQL service (ADR-0007), with no private backdoors.
