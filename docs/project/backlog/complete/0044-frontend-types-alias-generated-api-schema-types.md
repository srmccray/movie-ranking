---
id: '0044'
title: 'frontend/src/types/index.ts: replace hand-written API types with aliases to
  the generated schema'
status: Complete
dependencies:
- TASK-0043
- TASK-0017
governing_adrs:
- ADR-0012
governing_prds:
- PRD-0006
governing_stories:
- US-0006
target_bc: frontend
---

# TASK-0044: frontend/src/types/index.ts: replace hand-written API types with aliases to the generated schema

## Summary
With the schema generated (TASK-0043), derive the API-shaped types in `frontend/src/types/index.ts` from it so a backend schema change becomes a compile error in the frontend. Keep UI-only types as they are.

Priority: P3. Size: M. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- API-shaped types to alias (current lines in `src/types/index.ts`): `Token` (3), `GoogleAuthUrlResponse` (9), `UserProfileResponse` (25), `Movie` (34), `TMDBSearchResult` (58), `Ranking` (71), `RankingWithMovie` (80), `RankingListResponse` (89), `ActivityDay`/`ActivityResponse` (107-112), `GenreStats`/`GenreResponse` (118-125), `StatsResponse` (130), `RatingCount`/`RatingDistributionResponse` (139-144), `UserCreate` (151), `MovieCreate` (156), `RankingCreate` (169), `ParsedMovieItem`, `TMDBMatchResult`, `MatchedMovieItem`, `ImportSessionResponse`, `ImportSessionDetailResponse`, `ImportMovieAddRequest`, `ImportMovieMatchRequest` (209-283). Write them as `export type Ranking = components["schemas"]["RankingResponse"];` using a local `type Schemas = components["schemas"]` alias.
- Keep as hand-written (not part of the API): `GoogleCallbackError`, `AccountLinkingResponse` if it is not a schema, `SortField`/`SortOrder`/`SortOption`, `ApiError`, `ValidationError`, `AuthState`, `AuthContextType`, `MovieBrief` (check whether the backend has a matching schema first).
- Expect `tsc -b` to surface real mismatches (optional vs required fields, `string` vs `Date`, `null` vs `undefined`); fix call sites rather than casting. The 17 files that import from `@/types` or relative `../types` are the blast radius (`grep -rn "from '@/types'\|from '../types'" frontend/src`).
- If the diff grows beyond roughly 500 changed lines, split by domain (auth/movies/rankings first, analytics, import) into follow-up PRs; keep each PR green.

## Notes and Risks
- TASK-0027 and TASK-0045 add schemas; they appear in the generated file automatically and need aliases only when the UI uses them.
- Do not change runtime behavior; this is a typing change. Frontend tests (`npm run test:run`) must pass unchanged.
- After adoption, shrink the manual contract checklist in the root `CLAUDE.md` to the trailing-slash rule and the wrapper-response reminder.

## Dependencies
- TASK-0043 generates the file.
- TASK-0017: finalises the import response shapes' source files so the aliases are not immediately re-edited (soft ordering).

## Definition of Done
- [ ] The API-shaped types listed above are aliases to `components["schemas"]` types (no duplicate field lists remain for them).
- [ ] `cd frontend && npx tsc -b`, `npm run lint` and `npm run test:run` pass with the same test count.
- [ ] Renaming a field in a backend response schema and regenerating produces `tsc` errors at the frontend usage sites (demonstrated in the PR description).
- [ ] The root `CLAUDE.md` contract checklist no longer asks contributors to hand-copy field lists.

```gherkin
Scenario: A backend field rename breaks the frontend build
  Given the frontend types alias the generated schema
  When a response field is renamed in app/schemas and the schema is regenerated
  Then `tsc -b` fails at the components that read the old field name
```

## INVEST Criteria
- **Independent**: Ordered after TASK-0043, TASK-0017 (see Dependencies); otherwise executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Turns the manual API Contract Verification checklist into compiler checks; ADR-0012, PRD-0006, US-0006.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Medium: one PR touching several files; keep it under about 500 lines of changed source (excluding generated files and migrations' SQL boilerplate).
- **Testable**: Compiler output after a deliberate schema change (ADR-0012).
