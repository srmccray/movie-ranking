---
id: '0008'
title: "Resume an import review without losing progress"
status: Accepted
created: 2026-10-14
persona: "Casey (The Movie Enthusiast)"
target_bc: "backend"
feature: "FEAT-BACK-08"
governing_prd: "PRD-0006"
scenarios:
  - "Review continues after the server restarts"
  - "An expired session is rejected"
---

# US-0008 — Resume an import review without losing progress

## Governing PRD
- [`PRD-0006: Platform Foundations`](../../product/accepted/prd-0006-platform-foundations.md)

## User Story

**As** Casey (The Movie Enthusiast),
**I want** my Amazon Prime import review to survive server restarts and different server instances,
**So that** I do not get "Import session not found or expired" in the middle of reviewing hundreds of titles.

## Acceptance Criteria

```gherkin
Scenario: Review continues after the server restarts
  Given Casey uploaded an Amazon Prime CSV and added 3 movies from the review list
  When the backend process restarts
  And Casey requests the same import session
  Then the session is returned with 3 movies marked "added" and the current index unchanged
```

```gherkin
Scenario: An expired session is rejected
  Given Casey's import session is older than 30 minutes
  When Casey requests the session
  Then the response is 404 "Import session not found or expired"
```
