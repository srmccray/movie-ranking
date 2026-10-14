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
Playwright is not yet set up in this repository: there is no Playwright dependency or browser test suite. Current automated tests are `pytest` (backend, `tests/`) and Vitest with MSW (frontend, `frontend/src/**/*.test.ts(x)`). The Gherkin scenarios in `docs/project/user_stories/accepted/` are therefore not yet executed as Playwright suites, and UI tasks in `backlog/complete/` (TASK-0005, TASK-0006) were completed before this ADR was adopted.
