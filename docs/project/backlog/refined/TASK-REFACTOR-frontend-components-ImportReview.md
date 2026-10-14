---
id: REFACTOR-frontend-components-ImportReview
title: Refactor and Decompose Legacy File ImportReview.tsx
status: Refined
governing_adrs:
- ADR-0002
governing_prds:
- PRD-0005
governing_stories:
- US-0005
target_bc: core
---

# TASK-REFACTOR-frontend-components-ImportReview: Refactor Legacy File ImportReview.tsx

## Summary
The grandfathered debt file `frontend/src/components/ImportReview.tsx` contains 505 lines and violates the hard file length invariant governed by ADR-0002 (<500 lines).
This task plans the incremental extraction of cohesive submodules (ImportReview_movie.ts, ImportReview_search.ts) and establishes a public barrel export facade.

## Target Submodule Decomposition Path
Target decomposition destination: `frontend/src/components/ImportReview/` with submodules:
- `ImportReview_movie.ts`: currentMovie, handleSelectMovie, updatedMovie, movie, ImportReviewProps, DEBOUNCE_DELAY, MAX_RESULTS, ImportReview, inputRef, resultsRef, debounceTimerRef, pendingMovies, progress, handleAdd, ratedAt, handleSkip, results, items, highlightedItem, initialQuery, isUnmatched, confidenceLabel
- `ImportReview_search.ts`: performSearch, handleSearchOpen, handleSearchClose, handleSearchKeyDown

## AST Decomposition Blueprint
Decomposition Blueprint for /Users/stephen/Projects/movie-ranking/frontend/src/components/ImportReview.tsx (505 lines):
  Submodule 'ImportReview_movie.ts' (~22 lines):
    - [const] currentMovie (lines 46-46)
    - [const] handleSelectMovie (lines 185-185)
    - [const] updatedMovie (lines 191-191)
    - [const] movie (lines 267-267)
    - [interface] ImportReviewProps (lines 7-7)
    - [const] DEBOUNCE_DELAY (lines 17-17)
    - [const] MAX_RESULTS (lines 18-18)
    - [function] ImportReview (lines 20-20)
    - [const] inputRef (lines 42-42)
    - [const] resultsRef (lines 43-43)
    - [const] debounceTimerRef (lines 44-44)
    - [const] pendingMovies (lines 47-47)
    - [const] progress (lines 48-48)
    - [const] handleAdd (lines 50-50)
    - [const] ratedAt (lines 61-61)
    - [const] handleSkip (lines 75-75)
    - [const] results (lines 106-106)
    - [const] items (lines 143-143)
    - [const] highlightedItem (lines 144-144)
    - [const] initialQuery (lines 168-168)
    - [const] isUnmatched (lines 268-268)
    - [const] confidenceLabel (lines 269-269)
  Submodule 'ImportReview_search.ts' (~4 lines):
    - [const] performSearch (lines 94-94)
    - [const] handleSearchOpen (lines 167-167)
    - [const] handleSearchClose (lines 176-176)
    - [const] handleSearchKeyDown (lines 222-222)
  Suggested barrel exports:
    export * from "./ImportReview_movie";
    export * from "./ImportReview_search";

## INVEST Criteria
- **Independent**: Executed in isolated task branch without modifying shared backlog on branch.
- **Negotiable**: Concrete boundaries derived from AST seams.
- **Valuable**: Retires grandfathered technical debt from `.specops/grandfathered_debt.json`.
- **Estimable**: Symbol-level decomposition blueprint provided.
- **Small (<500 lines)**: Target submodules each strictly under 400 lines.
- **Testable**: Validated via blackbox frontdoor tests (ADR-0003).
