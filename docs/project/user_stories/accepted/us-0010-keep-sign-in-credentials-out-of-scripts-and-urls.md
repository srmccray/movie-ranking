---
id: '0010'
title: "Keep sign-in credentials out of scripts and URLs"
status: Accepted
created: 2026-10-14
persona: "Casey (The Movie Enthusiast)"
target_bc: "backend"
feature: "FEAT-BACK-10"
governing_prd: "PRD-0007"
scenarios:
  - "The session token is not readable by page scripts"
  - "Google sign-in leaves no token in the URL"
  - "Cross-site requests cannot act as Casey"
  - "Login attempts are rate limited"
---

# US-0010 — Keep sign-in credentials out of scripts and URLs

## Governing PRD
- [`PRD-0007: Operational Safety`](../../product/accepted/prd-0007-operational-safety.md)

## User Story

**As** Casey (The Movie Enthusiast),
**I want** my sign-in session to be unreadable by page scripts, absent from URLs and protected from forged requests and password guessing,
**So that** a script injection, a shared link or a malicious site cannot take over my rankings.

## Acceptance Criteria

```gherkin
Scenario: The session token is not readable by page scripts
  Given Casey signs in with email and password
  When Casey opens the browser console on the rankings page
  Then `document.cookie` does not contain the session token
  And localStorage has no "movie_ranking_token" entry
  And the rankings page still loads
```

```gherkin
Scenario: Google sign-in leaves no token in the URL
  Given Casey completes Google sign-in
  When the browser lands on the app after the callback
  Then the address bar and browser history contain no "token=" parameter
  And Casey is signed in
```

```gherkin
Scenario: Cross-site requests cannot act as Casey
  Given Casey is signed in with a session cookie
  When a request DELETE /api/v1/rankings/all/ arrives with the cookie but without the X-CSRF-Token header
  Then the response is 403 and no rankings are deleted
```

```gherkin
Scenario: Login attempts are rate limited
  Given one IP address sends more login requests per minute than the configured limit
  When it sends another POST /api/v1/auth/login request
  Then the response is rejected at the edge with HTTP 429 or 403
```
