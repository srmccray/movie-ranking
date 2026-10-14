---
id: '0005'
title: Legacy File Decomposition
status: Accepted
created: 2026-10-13
target_persona: Alex (The Systems Builder)
component: core
---

# PRD-0005 — Legacy File Decomposition

## Who this is for

- **Alex (The Systems Builder)**: maintains movie-ranking with AI coding agents and needs every file small enough for an agent to read and change safely.

## What the person cannot do today

- Eleven legacy files exceed the 500-line limit set by ADR-0002 and are grandfathered in `.specops/grandfathered_debt.json`. Agents editing them lose context, produce noisy diffs, and risk regressions; the grandfather list also means the invariant is not fully enforced.

## What good looks like

1. **Decomposed modules**: each grandfathered file is split into focused, single-responsibility modules with unchanged public behavior (same API routes, components, and test coverage).
2. **Shrinking debt**: each split removes its entry from the grandfathered debt baseline.

## What this does not do

- No behavior, API, or UI changes; this is structural refactoring only.
- Does not cover files approaching the limit (`tests/test_csv_parser.py`, `tests/test_tmdb_service.py`, `app/routers/analytics.py`) unless they cross 500 lines.

## Checkable Outcomes

1. `spec-ops health` reports zero grandfathered debt items.
2. Every source file in `app/`, `frontend/src/`, `infra/lib/`, and `tests/` is under 500 lines.
3. `venv/bin/pytest` and the frontend test suite pass with the same test count before and after each split.
4. API endpoints under `/api/v1/` respond identically (status codes and response shapes) after the backend splits.

## Linked User Stories

- [US-0005: Keep every source file under 500 lines](../../user_stories/accepted/us-0005-keep-every-source-file-under-500-lines.md)

## Implementing Backlog Tasks

- TASK-REFACTOR-app-routers-google_auth
- TASK-REFACTOR-app-routers-import_amazon
- TASK-REFACTOR-frontend-__tests__-mocks-handlers
- TASK-REFACTOR-frontend-components-ImportReview
- TASK-REFACTOR-frontend-components-MovieSearch.test
- TASK-REFACTOR-frontend-index
- TASK-REFACTOR-frontend-styles-pages-analytics
- TASK-REFACTOR-frontend-styles-pages-import
- TASK-REFACTOR-tests-test_auth
- TASK-REFACTOR-tests-test_google_auth
- TASK-REFACTOR-tests-test_import_amazon
- TASK-REFACTOR-tests-test_import_session
- TASK-REFACTOR-tests-test_movies
