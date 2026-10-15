---
id: '0012'
title: 'frontend: delete the unused VITE_API_BASE_URL setting and the unused ImportCompletionSummary type'
status: Proposed
governing_adrs:
- ADR-0002
governing_prds:
- PRD-0006
governing_stories:
- US-0007
dependencies: []
target_bc: frontend
priority: P3
---

# TASK-0012: frontend: delete the unused VITE_API_BASE_URL setting and the unused ImportCompletionSummary type

## Summary
`frontend/.env.example` advertises `VITE_API_BASE_URL=/api/v1`, but no code reads it: `src/api/client.ts` hard-codes `API_BASE = '/api/v1'`. The product owner decided to delete the setting rather than wire it up. Remove the example file entry and the documentation that describes it.

Priority: P3. Size: XS. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- `frontend/.env.example` contains only a header comment, a two-line comment and `VITE_API_BASE_URL=/api/v1` (line 5). Since it holds no other variable, delete the whole file.
- `frontend/README.md:120` says `.env.example` lists `VITE_API_BASE_URL` but no code reads it: rewrite the paragraph to say the base path is the fixed `/api/v1` constant and `/api/*` must be routed to the backend.
- `frontend/CLAUDE.md:609` says the `VITE_API_BASE_URL` in `.env.example` is not read by any code: delete that parenthetical.
- `grep -rn VITE_API_BASE_URL --exclude-dir=node_modules .` must return nothing afterwards (also check `frontend/src/vite-env.d.ts`, `vite.config.ts`, `Dockerfile`, `docker-compose.yml`, `.github/workflows/*.yml`).
- Frontend twin of the dead backend schema in TASK-0011: `frontend/src/types/index.ts:296-303` defines `ImportCompletionSummary` (`movies_added`, `movies_skipped`, `unmatched_titles`), and `grep -rn ImportCompletionSummary frontend/src` finds no other use. Delete it. (`getGenres` and `getActivity` in `client.ts` are used by `AnalyticsPage.tsx` and `ActivityChart.tsx`, so they stay.)

## Notes and Risks
- Pure documentation and config cleanup; no runtime change. `API_BASE` stays hard-coded.
- `API_PROXY_TARGET` (used by `vite.config.ts` and the Playwright config) is a different variable and stays.

## Definition of Done
- [ ] `grep -rn VITE_API_BASE_URL --exclude-dir=node_modules .` from the repository root returns nothing, and `grep -rn ImportCompletionSummary frontend/src` returns nothing.
- [ ] `cd frontend && npm run build` still exits 0.
- [ ] `frontend/README.md` and `frontend/CLAUDE.md` describe `API_BASE` as the fixed `/api/v1` path.

```gherkin
Scenario: The unused setting is gone
  Given VITE_API_BASE_URL is removed from .env.example and the docs
  When the repository is searched for VITE_API_BASE_URL
  Then there are no matches
  And the frontend still builds
```

## INVEST Criteria
- **Independent**: No task dependencies; executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Stops contributors setting a variable that does nothing; PRD-0006, US-0007.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Extra small: a handful of lines in one or two files.
- **Testable**: A repository-wide search and a successful build prove the removal (ADR-0002 keeps docs and code consistent).
