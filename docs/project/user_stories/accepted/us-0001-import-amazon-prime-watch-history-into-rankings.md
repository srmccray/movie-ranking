---
id: '0001'
title: Import Amazon Prime Watch History into Rankings
status: Accepted
created: 2026-10-13
persona: Casey (The Movie Enthusiast)
governing_prd: PRD-0001
---

# US-0001 — Import Amazon Prime Watch History into Rankings

## Governing PRD
- [`PRD-0001: Amazon Prime Watch History Import`](../../product/shipped/prd-0001-amazon-prime-watch-history-import.md)

## User Story

**As a** movie enthusiast,  
**I want** to upload my Amazon Prime Video watch-history CSV and review each matched movie,  
**So that** I can populate my rankings without searching for every movie by hand.

## Acceptance Criteria

```gherkin
Scenario: Uploading a Prime CSV produces an import summary
Given Casey is logged in and on the Settings page
When Casey clicks "Import" under "Import Watch History", then uploads a CSV containing 3 movies and 2 TV episodes in the "Import from Amazon Prime" wizard
Then the response from POST "/api/v1/import/amazon-prime/upload/" is 201
And the summary reports 2 TV shows filtered and the movies ready for review
```

```gherkin
Scenario: Adding a reviewed movie creates a ranking dated to the watch date
Given an active import session with a matched movie watched on "2024-01-15"
When Casey rates it 4 stars and clicks "Add to My Movies"
Then the movie appears in Casey's rankings with rating 4 and rated date 2024-01-15
```

```gherkin
Scenario: Already-ranked movies are skipped
Given Casey has already ranked "The Dark Knight"
When Casey uploads a CSV containing "The Dark Knight"
Then the summary counts it as already ranked and it is not offered for review
```

```gherkin
Scenario: Completing the review shows a summary
Given Casey has added or skipped every movie in the session
Then the completion screen shows the number of movies added and skipped
```
