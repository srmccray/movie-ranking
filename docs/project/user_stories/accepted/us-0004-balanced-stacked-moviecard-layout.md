---
id: '0004'
title: Balanced Stacked MovieCard Layout
status: Accepted
created: 2026-10-13
persona: Casey (The Movie Enthusiast)
governing_prd: PRD-0004
---

# US-0004 — Balanced Stacked MovieCard Layout

## Governing PRD
- [`PRD-0004: MovieCard Layout Redesign`](../../product/shipped/prd-0004-moviecard-layout-redesign.md)

## User Story

**As a** movie enthusiast,  
**I want** to see each ranked movie in a compact stacked card,  
**So that** my list looks balanced and easy to scan.

## Acceptance Criteria

```gherkin
Scenario: Card shows stacked movie information
Given Casey has ranked movies
When Casey views the rankings list
Then each card shows poster, title, year, genres, star rating and rated date stacked beside the poster
And the kebab menu is in the top-right corner
```

```gherkin
Scenario: Card interactions still work
Given Casey is viewing a movie card
When Casey changes the star rating, edits the rated date, or deletes via the kebab menu
Then each action succeeds and the delete confirmation covers the whole card
```
