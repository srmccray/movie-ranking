# ADR-0002: Modular Source File Length Limit (<500 Lines Anti-Rot Rule)

## Status
Accepted

## Context
Large monolithic files (>500 lines) are the primary cause of architectural decay and LLM degradation in AI-assisted codebases. When files grow too large, coding agents suffer from lost attention, generate conflicting diffs, and introduce subtle regressions.

## Decision
We establish a non-negotiable **Hard Invariant: Source files must remain under 500 lines**:
1. Any module approaching or exceeding 500 lines must be proactively decomposed into single-responsibility submodules (e.g. modular routers, domain handlers, or split test suites).
2. The `spec-ops health` scanner verifies this rule continuously. Pull requests violating this limit will be blocked.

## Consequences
- **Positive**: Sharp LLM attention windows, faster code reviews, clean surgical diffs, and modular decoupled architectures.
- **Negative**: Increases the number of files and requires explicit barrel exports (`__init__.py` or index modules).

## Project Note (movie-ranking)
`spec-ops health` also scans `.css` files. Thirteen pre-existing files over the limit are grandfathered in `specops.toml` and `.specops/grandfathered_debt.json`; they are tracked by `TASK-REFACTOR-*` backlog tasks under PRD-0005. Frontend splits use `index.ts` re-exports or additional `@import` lines in `frontend/src/styles/index.css`, and backend splits use package `__init__.py` files.
