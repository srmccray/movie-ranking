---
id: REFACTOR-frontend-components-MovieSearch.test
title: Refactor and Decompose Legacy File MovieSearch.test.tsx
status: Proposed
created: 2026-09-29
governing_adrs:
  - ADR-0002
target_bc: core
---

# TASK-REFACTOR-frontend-components-MovieSearch.test: Refactor Legacy File MovieSearch.test.tsx

## Summary
The grandfathered debt file `frontend/src/components/MovieSearch.test.tsx` contains 515 lines and violates the hard file length invariant governed by ADR-0002 (<500 lines).
This task plans the incremental extraction of cohesive submodules (MovieSearch.test_input.ts, MovieSearch.test_user.ts) and establishes a public barrel export facade.

## Target Submodule Decomposition Path
Target decomposition destination: `frontend/src/components/MovieSearch.test/` with submodules:
- `MovieSearch.test_input.ts`: input, input, input, input, input, input, input, input, input, input, input, input, input, input, input, input, input, input, input, input, input, input, input, input, input, renderMovieSearch, results, options, spinner, fetchSpy, searchCalls, searchCallsAfter, images, options, options, options, onSelect, options, numOptions, options, options, onSelect, options, alert, alert, alert
- `MovieSearch.test_user.ts`: user, user, user, user, user, user, user, user, user, user, user, user, user, user, user, user, user, user, user, user, user, user

## AST Decomposition Blueprint
Decomposition Blueprint for /Users/stephen/Projects/movie-ranking/frontend/src/components/MovieSearch.test.tsx (515 lines):
  Submodule 'MovieSearch.test_input.ts' (~46 lines):
    - [const] input (lines 56-56)
    - [const] input (lines 64-64)
    - [const] input (lines 73-73)
    - [const] input (lines 83-83)
    - [const] input (lines 102-102)
    - [const] input (lines 122-122)
    - [const] input (lines 139-139)
    - [const] input (lines 151-151)
    - [const] input (lines 166-166)
    - [const] input (lines 201-201)
    - [const] input (lines 220-220)
    - [const] input (lines 237-237)
    - [const] input (lines 256-256)
    - [const] input (lines 275-275)
    - [const] input (lines 298-298)
    - [const] input (lines 322-322)
    - [const] input (lines 340-340)
    - [const] input (lines 365-365)
    - [const] input (lines 389-389)
    - [const] input (lines 409-409)
    - [const] input (lines 436-436)
    - [const] input (lines 452-452)
    - [const] input (lines 468-468)
    - [const] input (lines 485-485)
    - [const] input (lines 501-501)
    - [function] renderMovieSearch (lines 30-30)
    - [const] results (lines 94-94)
    - [const] options (lines 112-112)
    - [const] spinner (lines 129-129)
    - [const] fetchSpy (lines 163-163)
    - [const] searchCalls (lines 177-177)
    - [const] searchCallsAfter (lines 186-186)
    - [const] images (lines 229-229)
    - [const] options (lines 246-246)
    - [const] options (lines 267-267)
    - [const] options (lines 289-289)
    - [const] onSelect (lines 295-295)
    - [const] options (lines 349-349)
    - [const] numOptions (lines 350-350)
    - [const] options (lines 377-377)
    - [const] options (lines 398-398)
    - [const] onSelect (lines 406-406)
    - [const] options (lines 418-418)
    - [const] alert (lines 442-442)
    - [const] alert (lines 458-458)
    - [const] alert (lines 474-474)
  Submodule 'MovieSearch.test_user.ts' (~22 lines):
    - [const] user (lines 80-80)
    - [const] user (lines 99-99)
    - [const] user (lines 119-119)
    - [const] user (lines 136-136)
    - [const] user (lines 148-148)
    - [const] user (lines 162-162)
    - [const] user (lines 198-198)
    - [const] user (lines 217-217)
    - [const] user (lines 234-234)
    - [const] user (lines 253-253)
    - [const] user (lines 272-272)
    - [const] user (lines 294-294)
    - [const] user (lines 319-319)
    - [const] user (lines 337-337)
    - [const] user (lines 362-362)
    - [const] user (lines 386-386)
    - [const] user (lines 405-405)
    - [const] user (lines 432-432)
    - [const] user (lines 448-448)
    - [const] user (lines 464-464)
    - [const] user (lines 482-482)
    - [const] user (lines 498-498)
  Suggested barrel exports:
    export * from "./MovieSearch.test_input";
    export * from "./MovieSearch.test_user";

## INVEST Criteria
- **Independent**: Executed in isolated task branch without modifying shared backlog on branch.
- **Negotiable**: Concrete boundaries derived from AST seams.
- **Valuable**: Retires grandfathered technical debt from `.specops/grandfathered_debt.json`.
- **Estimable**: Symbol-level decomposition blueprint provided.
- **Small (<500 lines)**: Target submodules each strictly under 400 lines.
- **Testable**: Validated via blackbox frontdoor tests (ADR-0003).
