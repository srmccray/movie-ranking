---
id: 0008
title: 'frontend: fix all tsc -b errors and eslint problems'
status: Complete
governing_adrs:
- ADR-0004
governing_prds:
- PRD-0006
governing_stories:
- US-0006
target_bc: frontend
---

# TASK-0008: frontend: fix all tsc -b errors and eslint problems

## Summary
`npx tsc -b` reports 70 errors and `npm run lint` reports 9 problems (7 errors, 2 warnings) in `frontend/`, which is why `.github/workflows/ci.yml` deliberately skips both (comment at line 87). One of the errors is in production code (`src/api/client.ts`). Fix every one so both commands exit 0; adding them to CI is a separate task (TASK-0009).

Priority: P1. Size: M. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- Measured on main (c81de14) with `cd frontend && npx tsc -b` and `npx eslint .`. tsc errors by cause:
- **Missing vitest globals (57 errors: TS2304 x38, TS2582 x19)**: `frontend/tsconfig.json` has no `types` entry while `vite.config.ts:33` sets `test.globals: true`. 45 of these are in `src/__tests__/SettingsPage.test.tsx`, which uses `describe`/`beforeEach`/`afterEach` without importing them. Fix: add `"types": ["vitest/globals"]` to `compilerOptions`.
- **`global` is not defined (12 errors)**: `src/api/client.test.ts` (11 uses of `vi.spyOn(global, 'fetch')`, first at line 38) and `src/components/MovieSearch.test.tsx:161`. Fix: use `globalThis`.
- **`HeadersInit` indexed like a record (3 errors, TS7053)**: `src/api/client.ts:43-57` (`headers['Authorization']`, `headers['Content-Type']`) and `src/api/client.ts:209-211` in `uploadAmazonPrimeCSV`. Fix: type the local variable `Record<string, string>` (do not switch to a `Headers` object: `client.test.ts` lines 44, 104, 149, 168 read `options.headers` as a plain object).
- **Implicit any `call` (3 errors, TS7006)**: `src/api/client.test.ts:236`, `src/components/MovieSearch.test.tsx:175` and `:184`. Fix: annotate the callback parameter.
- **TS2488** `src/context/AuthContext.test.tsx:42`: a `Mock` is destructured as an iterable; type the mock or access it by property.
- **Unused symbols (TS6133 x6, same as the eslint errors)**: `src/__tests__/setup.ts:13` `beforeEach`; `src/components/ActivityChart.tsx:15` `DAYS`; `src/components/MovieSearch.test.tsx:127` `spinner`; `src/context/AuthContext.test.tsx:14` `act` and `:40` `TestAuthErrorConsumer`; `src/pages/LoginPage.test.tsx:14` `vi`. Delete them (or use them if the test was meant to).
- **eslint only**: `src/components/ActivityChart.tsx:63` `prefer-const` on `currentDate`; warning `src/context/AuthContext.tsx:102` (react-refresh/only-export-components: move the hook out of the provider file or add a documented disable); warning `src/pages/RankingsPage.tsx:48` (react-hooks/exhaustive-deps for `fetchRankings`: wrap in `useCallback` or include it).

## Notes and Risks
- Setting `types` in tsconfig stops TypeScript auto-including every `@types/*` package. If `tsc -b` then reports a missing global, add that package to the array rather than removing `types`.
- Behavior of production code must not change; the `client.ts` edit is type-only. `src/api/client.test.ts` is the safety net for it.
- Do not silence errors with `@ts-ignore`, `any` casts or blanket eslint disables; one documented disable is acceptable for the react-refresh warning only.

## Definition of Done
- [ ] `cd frontend && npx tsc -b` exits 0 with no output.
- [ ] `cd frontend && npm run lint` exits 0 with 0 errors and 0 warnings.
- [ ] `cd frontend && npm run test:run` passes with the same number of tests as before the change.
- [ ] `cd frontend && npm run build` (`tsc -b && vite build`) exits 0.
- [ ] No `@ts-ignore`, `@ts-expect-error` or `as any` was added in `frontend/src`.

```gherkin
Scenario: Frontend type check and lint are clean
  Given the fixes in this task are applied
  When `npx tsc -b` and `npm run lint` run in frontend/
  Then both exit 0
  And `npm run test:run` reports the same test count as before
```

## INVEST Criteria
- **Independent**: No task dependencies; executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Unblocks enforcing type and lint checks in CI (TASK-0009); removes a real type error in `src/api/client.ts`; PRD-0006 outcome 1, US-0006.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Medium: one PR touching several files; keep it under about 500 lines of changed source (excluding generated files and migrations' SQL boilerplate).
- **Testable**: The commands in the Definition of Done are observable through public tooling (ADR-0003); no private state is inspected.
