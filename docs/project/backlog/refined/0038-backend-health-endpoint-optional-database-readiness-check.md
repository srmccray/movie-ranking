---
id: 0038
title: 'app/main.py: GET /health?deep=true checks the database and returns 503 when
  it is unreachable'
status: Refined
dependencies:
- TASK-0037
governing_adrs:
- ADR-0003
governing_prds:
- PRD-0007
governing_stories:
- US-0009
target_bc: backend
---

# TASK-0038: app/main.py: GET /health?deep=true checks the database and returns 503 when it is unreachable

## Summary
`GET /health` returns a static `{"status": "healthy", "version": "1.0.0"}` (`app/main.py:95-121`) even though its OpenAPI declares a 503 'Service is unhealthy' response that is never produced, and the startup database check does not run on Lambda (`lifespan="off"` in `lambda_handler.py`). Add an opt-in deep check so deploy verification and monitors can tell 'process up' from 'database reachable'.

Priority: P2. Size: XS. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- Keep `/health` exactly as is for load balancers (liveness, no database). Add a `deep: bool = False` query parameter: when true, run `SELECT 1` through the session dependency (`DbSession`) with a short timeout (2 s) and return `{"status": "healthy", "database": "ok"}`; on failure return HTTP 503 `{"status": "unhealthy", "database": "unreachable"}` and log the error with the request id.
- Path stays `/health` (documented trailing-slash exception) so the existing CloudFront behavior for `/health` (`movie-ranking-stack.ts:194`) routes it; a new `/health/ready/` path would not be proxied.
- Use it in `deploy.yml` after publishing: `curl --fail "https://<domain>/health?deep=true"` as a smoke test step (small edit; coordinate with TASK-0033).
- Update the OpenAPI example in the route and the root `CLAUDE.md` exception note if it mentions `/health`.

## Notes and Risks
- Do not expose database error text in the response body.
- Query parameters are kept out of logs by TASK-0037, which is fine for this boolean.

## Dependencies
- TASK-0037 reshapes `app/main.py` (logging setup, handlers); do this small change on top of it to avoid conflicts.

## Definition of Done
- [ ] `GET /health` still returns 200 without touching the database.
- [ ] `GET /health?deep=true` returns 200 with `"database": "ok"` when the database is up, and 503 with `"status": "unhealthy"` when the session dependency fails (test by overriding `get_db` to raise at the HTTP boundary).
- [ ] The deploy workflow smoke-tests `?deep=true` after publishing.

```gherkin
Scenario: The deep health check reports an unreachable database
  Given the database is unreachable
  When a client calls GET /health?deep=true
  Then the response status is 503 and the body status is "unhealthy"
  And GET /health without deep still returns 200
```

## INVEST Criteria
- **Independent**: Ordered after TASK-0037 (see Dependencies); otherwise executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Lets deploys and monitors verify real readiness; PRD-0007 outcome 6, US-0009.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Extra small: a handful of lines in one or two files.
- **Testable**: Public endpoint responses with the database dependency failing (ADR-0003).
