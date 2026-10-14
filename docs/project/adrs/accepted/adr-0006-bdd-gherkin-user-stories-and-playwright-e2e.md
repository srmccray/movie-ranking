# ADR-0006: Behavior-Driven Development (BDD) with Gherkin User Stories and Playwright

## Status
Accepted

## Context
Requirements written as passive prose frequently diverge from actual UI implementations, resulting in untested journeys, broken client-side routing, and dead buttons.

## Decision
We adopt **Behavior-Driven Development (BDD)**:
1. User stories in `docs/project/user_stories/accepted/` must specify executable Gherkin scenarios (`Given ... When ... Then`).
2. Scenarios are automated via Playwright end-to-end browser tests running across Chromium, Firefox, and WebKit.
3. UI tasks cannot move to `complete/` until their Playwright BDD suite passes cleanly without backdoors.

## Consequences
- **Positive**: User stories act as living, executable test suites; guarantees consistent cross-browser user journeys.
- **Negative**: Browser automation suites take longer to execute than headless unit tests.

## Project Note (movie-ranking)
Playwright is set up in `frontend/` (`@playwright/test`, config in `frontend/playwright.config.ts`, specs in `frontend/e2e/`, run with `npm run test:e2e`). Only the **Chromium** project is configured today; Firefox and WebKit (called for above) are not yet added. The e2e run starts the real Vite dev server and the real FastAPI app on a throwaway SQLite database (`frontend/e2e/support/run_backend.py`), so no mocks or database backdoors are involved. Currently executed: US-0003 (both scenarios) and an auth smoke spec. US-0001, US-0002 (need TMDB), US-0004 and US-0005 are not yet automated, and the Playwright suite is not yet part of CI. Other automated tests remain `pytest` (backend, `tests/`) and Vitest with MSW (frontend, `frontend/src/**/*.test.ts(x)`). UI tasks in `backlog/complete/` (TASK-0005, TASK-0006) were completed before this ADR was adopted.
