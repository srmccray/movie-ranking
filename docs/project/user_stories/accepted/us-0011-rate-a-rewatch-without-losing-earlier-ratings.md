---
id: '0011'
title: "Rate a rewatch without losing earlier ratings"
status: Accepted
created: 2026-10-14
persona: "Casey (The Movie Enthusiast)"
target_bc: "backend"
feature: "FEAT-BACK-11"
governing_prd: "PRD-0008"
scenarios:
  - "A second rating keeps the first"
  - "Importing a repeat viewing keeps the earlier rating"
  - "Existing rankings become first watches"
---

# US-0011 — Rate a rewatch without losing earlier ratings

## Governing PRD
- [`PRD-0008: Rewatch History`](../../product/shaped/prd-0008-rewatch-history.md)

## User Story

**As** Casey (The Movie Enthusiast),
**I want** re-rating a movie I watched again to add to its history instead of replacing my earlier rating and date,
**So that** I can see how my opinion and viewing dates changed over time.

## Acceptance Criteria

```gherkin
Scenario: A second rating keeps the first
  Given Casey rated "Heat" 5 on 2025-01-10
  When Casey records a rewatch of "Heat" with rating 3 on 2026-02-01
  Then the rankings list shows "Heat" with rating 3
  And the watch history of that ranking lists the 2026-02-01 watch with rating 3 and the 2025-01-10 watch with rating 5
```

```gherkin
Scenario: Importing a repeat viewing keeps the earlier rating
  Given Casey already ranked "Heat" 5 with watched date 2025-01-10
  When Casey adds "Heat" from an Amazon Prime import review with watch date 2026-02-01 and rating 4
  Then the watch history lists both watches and the 2025-01-10 watch still has rating 5
```

```gherkin
Scenario: Existing rankings become first watches
  Given Casey has 120 rankings before the watches migration
  When the migration completes
  Then Casey has 120 watches, each dated with its ranking's rated_at
```
