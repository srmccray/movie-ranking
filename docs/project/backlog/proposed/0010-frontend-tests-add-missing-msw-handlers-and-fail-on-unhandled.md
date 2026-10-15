---
id: '0010'
title: 'frontend/src/__tests__/mocks: add missing MSW handlers and fail tests on unhandled requests'
status: Proposed
governing_adrs:
- ADR-0003
governing_prds:
- PRD-0006
governing_stories:
- US-0006
dependencies:
- TASK-0008
target_bc: frontend
priority: P2
---

# TASK-0010: frontend/src/__tests__/mocks: add missing MSW handlers and fail tests on unhandled requests

## Summary
`src/__tests__/setup.ts:44` starts MSW with `onUnhandledRequest: 'warn'`, so a test that calls an endpoint with no handler only prints a warning and gets a network error. Four endpoints that `src/api/client.ts` calls have no handler. Add them, then switch to `'error'` so missing mocks fail the test that needs them.

Priority: P2. Size: S. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- Existing handlers (`src/__tests__/mocks/handlers/`): `auth.ts` (register, login, me, google login/callback/link), `movies.ts` (movies search, `POST /movies/`, `POST /rankings/`, `GET /rankings/`, `GET /analytics/stats/`, `GET /analytics/rating-distribution/`), `import.ts` (upload, session get, add, skip, **PATCH match (already exists at import.ts:295, nothing to add)**, DELETE session). `server.ts` already registers `handlers` and `importHandlers`.
- Missing, called by `client.ts`: `GET /api/v1/analytics/activity/` (`getActivity`, line 181), `GET /api/v1/analytics/genres/` (`getGenres`, line 185), `DELETE /api/v1/rankings/:rankingId/` (`deleteRanking`, line 168) and `DELETE /api/v1/rankings/all/` (`clearAllRankings`, line 174).
- Add them to `handlers/movies.ts` (rankings) and a new `handlers/analytics.ts` (activity, genres, and move the two existing analytics handlers there), keep the 401-without-Bearer behavior of the existing handlers, and use response shapes from `app/schemas/analytics.py` (`ActivityResponse`: `activity`, `start_date`, `end_date`; `GenreResponse`: `genres`, `total_movies`). Register the new array in `handlers/index.ts`.
- `handlers/movies.ts` is 257 lines and `import.ts` is 377 (ADR-0002 warns at 400): do not grow `import.ts`.
- Change `setup.ts:44` to `server.listen({ onUnhandledRequest: 'error' })`.

## Notes and Risks
- Switching to `'error'` may expose tests that silently rely on an unmocked call (for example a page that fetches analytics on mount). Fix each by adding a handler or a per-test `server.use(...)`; do not weaken the setting.
- Mock auth handlers use no trailing slash for `/auth/login` and `/auth/register` on purpose; that matches the backend exception list in CLAUDE.md. Leave them.

## Dependencies
- TASK-0008 edits `frontend/src/__tests__/setup.ts` (removes the unused `beforeEach` import at line 13); doing this task second avoids a merge conflict in the same file.

## Definition of Done
- [ ] `setup.ts` uses `onUnhandledRequest: 'error'`.
- [ ] Handlers exist for `GET /analytics/activity/`, `GET /analytics/genres/`, `DELETE /rankings/:id/` and `DELETE /rankings/all/`.
- [ ] `cd frontend && npm run test:run` passes with at least the previous number of tests.
- [ ] A new test (or an existing one) demonstrates that calling an unmocked URL fails the test rather than warning.
- [ ] No handler file exceeds 400 lines.

```gherkin
Scenario: A test that calls an unmocked endpoint fails
  Given MSW is configured with onUnhandledRequest "error"
  When a test triggers a request to an endpoint without a handler
  Then the test fails with an unhandled request error naming the URL
```

## INVEST Criteria
- **Independent**: Ordered after TASK-0008 (see Dependencies); otherwise executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Stops frontend tests passing while exercising unmocked network calls; PRD-0006 outcome 2, US-0006.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Small: one focused PR, a few files, well under 500 lines of change.
- **Testable**: Observable through `npm run test:run` and a deliberate unmocked request (ADR-0003: frontdoor network boundary, no internal spying).
