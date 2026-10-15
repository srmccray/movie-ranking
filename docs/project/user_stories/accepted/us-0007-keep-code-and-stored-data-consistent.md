---
id: '0007'
title: "Keep code and stored data consistent"
status: Accepted
created: 2026-10-14
persona: "Alex (The Systems Builder)"
target_bc: "backend"
feature: "FEAT-BACK-07"
governing_prd: "PRD-0006"
scenarios:
  - "A film is stored once"
  - "Timestamps keep their UTC meaning across the conversion"
  - "Cleanup does not change behavior"
---

# US-0007 — Keep code and stored data consistent

## Governing PRD
- [`PRD-0006: Platform Foundations`](../../product/accepted/prd-0006-platform-foundations.md)

## User Story

**As** Alex (The Systems Builder),
**I want** dead code removed, shared helpers in one place and the database to match the documented conventions,
**So that** agents change one thing in one place and the data they read means what the docs say.

## Acceptance Criteria

```gherkin
Scenario: A film is stored once
  Given Casey and another user each add the film with TMDB id 603 through POST /api/v1/movies/
  When both requests complete
  Then both responses contain the same movie id
  And the first response status is 201 and the second is 200
```

```gherkin
Scenario: Timestamps keep their UTC meaning across the conversion
  Given a ranking whose rated_at is 2026-03-01T23:30:00+00:00 before the datetime migration
  When the migration runs and Casey calls GET /api/v1/rankings/
  Then rated_at is returned as 2026-03-01T23:30:00 with a UTC offset
  And the analytics activity endpoint places that ranking on 2026-03-01
```

```gherkin
Scenario: Cleanup does not change behavior
  Given the backend and frontend suites pass before a cleanup task
  When dead code is removed or duplicated helpers are merged
  Then both suites pass with the same test count
  And no API response shape changes
```
