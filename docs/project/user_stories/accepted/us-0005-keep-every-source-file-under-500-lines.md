---
id: '0005'
title: "Keep every source file under 500 lines"
status: Accepted
created: 2026-10-13
persona: "Alex (The Systems Builder)"
target_bc: "core"
feature: "FEAT-CORE-05"
governing_prd: "PRD-0005"
scenarios:
  - "Grandfathered debt is fully paid down"
  - "Decomposition preserves behavior"
---

# US-0005 — Keep every source file under 500 lines

## Governing PRD
- [`PRD-0005: Legacy File Decomposition`](../../product/accepted/prd-0005-legacy-file-decomposition.md)

## User Story

**As** Alex (The Systems Builder),
**I want** every source file in movie-ranking to stay under 500 lines,
**So that** AI agents can read and modify any module without losing context or causing regressions.

## Acceptance Criteria

```gherkin
Scenario: Grandfathered debt is fully paid down
  Given the legacy files listed in the grandfathered debt baseline
  When each file is decomposed into focused modules
  Then `spec-ops health` reports zero grandfathered debt items
  And no source file exceeds 500 lines

Scenario: Decomposition preserves behavior
  Given a grandfathered file has been split into modules
  When the backend and frontend test suites run
  Then all tests pass with the same test count as before the split
```
