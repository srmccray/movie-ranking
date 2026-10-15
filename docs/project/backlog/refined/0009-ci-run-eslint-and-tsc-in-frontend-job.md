---
id: 0009
title: 'ci.yml: run eslint and tsc -b in the Frontend Tests & Build job'
status: Refined
dependencies:
- TASK-0008
governing_adrs:
- ADR-0004
governing_prds:
- PRD-0006
governing_stories:
- US-0006
target_bc: infra
---

# TASK-0009: ci.yml: run eslint and tsc -b in the Frontend Tests & Build job

## Summary
The `Frontend Tests & Build` job in `.github/workflows/ci.yml` runs only `npm run test:run` and `npx vite build` (the `Run tests` and `Build frontend` steps). `vite build` does not type-check, so type regressions and lint errors reach `main`. Add lint and type-check steps and delete the comment explaining why they were skipped.

Priority: P1. Size: XS. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- `.github/workflows/ci.yml:87-89` is the comment `# Deliberately NOT run here: eslint (9 pre-existing problems), tsc -b / npm run build (70 pre-existing type errors in test files) and Playwright e2e ...`. Remove the eslint and tsc parts of it; keep the Playwright part (still accurate, see ADR-0006 Project Note).
- In the `frontend-tests` job (working directory `frontend`), add after `Install dependencies` and before `Run tests`: `npm run lint` and `npx tsc -b`. Replace the final `npx vite build` step with `npm run build` (`tsc -b && vite build`, `frontend/package.json` line 8) only if the type-check step is not kept separately; do not run `tsc -b` twice.
- `.github/workflows/ci.yml` is listed in the `health` and `python` path filters, so the next PR will also run `spec-ops health`; no action needed.

## Notes and Risks
- The job already runs on every pull request (no path filter) so the new steps always report and can be made required branch checks.
- `deploy.yml` `test-frontend` job only runs tests; it is replaced by the CI gate in TASK-0033, so do not edit it here.

## Dependencies
- TASK-0008 makes `tsc -b` and eslint pass; adding the steps earlier would turn CI red.

## Definition of Done
- [ ] A pull request with a deliberate TypeScript type error in `frontend/src` fails the `Frontend Tests & Build` job at the type-check step.
- [ ] A pull request with an unused variable in `frontend/src` fails the job at `npm run lint`.
- [ ] The `Frontend Tests & Build` job passes on the PR that introduces these steps.
- [ ] The stale 'Deliberately NOT run here' comment no longer mentions eslint or `tsc -b`.

```gherkin
Scenario: Type and lint errors fail the pull request
  Given a pull request that introduces a TypeScript type error in frontend/src
  When the CI Quality Gate workflow runs
  Then the "Frontend Tests & Build" job fails at the `tsc -b` step
```

## INVEST Criteria
- **Independent**: Ordered after TASK-0008 (see Dependencies); otherwise executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Makes type and lint regressions impossible to merge unnoticed; PRD-0006 outcome 1, US-0006 scenario 1.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Extra small: a handful of lines in one or two files.
- **Testable**: Verified by opening a throwaway PR with a deliberate error and observing the job result (ADR-0004 self-healing CI loop).
