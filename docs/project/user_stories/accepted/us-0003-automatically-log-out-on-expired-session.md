---
id: '0003'
title: Automatically Log Out on Expired Session
status: Accepted
created: 2026-10-13
persona: Casey (The Movie Enthusiast)
governing_prd: PRD-0003
---

# US-0003 — Automatically Log Out on Expired Session

## Governing PRD
- [`PRD-0003: Auto-Logout on 401 Unauthorized`](../../product/shipped/prd-0003-auto-logout-on-401-unauthorized.md)

## User Story

**As a** movie enthusiast,  
**I want** to be sent to the login page when my session has expired,  
**So that** I can re-authenticate instead of seeing cryptic errors.

## Acceptance Criteria

```gherkin
Scenario: Expired session redirects to login
Given Casey has an expired session cookie in the browser
When Casey opens the rankings page and the session check returns 401
Then the session cookie is gone
And Casey is redirected to "/login"
```

```gherkin
Scenario: Failed login still shows an error
Given Casey is on the login page
When Casey submits invalid credentials and the API returns 401
Then an error message is shown on the login form
```
