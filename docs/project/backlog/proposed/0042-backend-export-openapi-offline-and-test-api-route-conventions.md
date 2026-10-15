---
id: '0042'
title: 'scripts/export_openapi.py + tests: export the OpenAPI schema offline and test trailing-slash and response_model conventions'
status: Proposed
governing_adrs:
- ADR-0012
- ADR-0003
governing_prds:
- PRD-0006
governing_stories:
- US-0006
dependencies: []
target_bc: backend
priority: P2
---

# TASK-0042: scripts/export_openapi.py + tests: export the OpenAPI schema offline and test trailing-slash and response_model conventions

## Summary
ADR-0012 makes the FastAPI OpenAPI document the source of truth for frontend types. Provide the offline exporter (no server, no database) that writes `frontend/openapi.json`, and turn two documented conventions into executable checks: all `/api/v1` routes end with `/` (except the two documented exceptions) and every route declares its response.

Priority: P2. Size: S. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- Exporter `scripts/export_openapi.py`: set dummy `DATABASE_URL=sqlite+aiosqlite:///:memory:`, `SECRET_KEY` and `TMDB_API_KEY` via `os.environ.setdefault` before importing `app.main` (the app builds its engine at import time but does not connect), then `json.dump(app.openapi(), indent=2, sort_keys=True)` to the path given by `--out` (default `frontend/openapi.json`), with a trailing newline so diffs are stable. Verified on main: `app.openapi()` imports without a database and returns 31 component schemas (about 59 KB).
- Route inventory on main (25 `APIRoute`s, from `app.routes`): only `POST /api/v1/auth/register` and `POST /api/v1/auth/login` lack a trailing slash (the documented exceptions), and the only route without a `response_model` is `GET /api/v1/auth/google/link/callback/` (returns a redirect; set `response_class=RedirectResponse` and `response_model=None` explicitly so intent is visible). `/health` and `/` are outside `/api/v1`.
- Test `tests/test_api_conventions.py` using the public OpenAPI document (`from app.main import app; app.openapi()["paths"]`): assert every path under `/api/v1` ends with `/` except `{"/api/v1/auth/register", "/api/v1/auth/login"}`, and every operation either has a JSON response schema in its success response or a 204/redirect status. Keep the exception set in the test so adding an exception is a reviewed change.
- Docs: add the export command to the root `CLAUDE.md` 'API Contract Verification' section and to `app/CLAUDE.md`.

## Notes and Risks
- `tests/conftest.py` builds its own FastAPI app; the convention test imports `app.main.app` directly, which is safe because `conftest.py` sets default environment variables before import (lines 17-26).
- Committing `frontend/openapi.json` happens in TASK-0043; this task only provides the script and checks.
- Routes added by other tasks (for example `GET/POST /rankings/{id}/watches/` in TASK-0027 or `POST /auth/logout/` in TASK-0045) must satisfy the same test; the exception list should not grow.

## Definition of Done
- [ ] `python scripts/export_openapi.py --out /tmp/openapi.json` succeeds without a running database and a second run produces a byte-identical file.
- [ ] `tests/test_api_conventions.py` passes, and fails when a route such as `@router.get("/foo")` (no trailing slash) is added to an `/api/v1` router.
- [ ] `GET /api/v1/auth/google/link/callback/` declares its redirect response explicitly.
- [ ] `venv/bin/pytest` passes.

```gherkin
Scenario: A route without a trailing slash fails the suite
  Given a new route is added at /api/v1/rankings/export without a trailing slash
  When the backend test suite runs
  Then tests/test_api_conventions.py fails and names the route
```

## INVEST Criteria
- **Independent**: No task dependencies; executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Makes the trailing-slash rule executable and gives the frontend a reproducible contract artifact; ADR-0012, PRD-0006 outcome 10, US-0006.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Small: one focused PR, a few files, well under 500 lines of change.
- **Testable**: Pytest result and a deterministic exported file (ADR-0003: the public OpenAPI document is the front door).
