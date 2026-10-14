---
id: '0002'
title: Manually Search for a Movie During Import Review
status: Accepted
created: 2026-10-13
persona: Casey (The Movie Enthusiast)
governing_prd: PRD-0002
---

# US-0002 — Manually Search for a Movie During Import Review

## Governing PRD
- [`PRD-0002: Manual Movie Search in Import Wizard`](../../product/shipped/prd-0002-manual-movie-search-in-import-wizard.md)

## User Story

**As a** movie enthusiast,  
**I want** to search TMDB for the right movie when an import match is wrong or missing,  
**So that** my import is complete and accurate.

## Acceptance Criteria

```gherkin
Scenario: Correcting a wrong match
Given Casey is reviewing an imported movie with a low-confidence match
When Casey clicks "Search for different movie", searches for the correct title and selects a result
Then PATCH "/api/v1/import/amazon-prime/session/{session_id}/movie/{index}/match/" returns the updated movie
And the review shows the newly selected movie ready for rating
```

```gherkin
Scenario: Resolving an unmatched movie
Given Casey is reviewing an imported movie with no TMDB match
When Casey clicks "Search for this movie" and selects a result
Then the movie can be rated and added
```

```gherkin
Scenario: Cancelling a search
Given the inline search is open
When Casey cancels it
Then the review returns to the previous movie state
```
