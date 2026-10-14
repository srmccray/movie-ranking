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
**I want** to be sent to the login page when my token has expired,  
**So that** I can re-authenticate instead of seeing cryptic errors.

## Acceptance Criteria

```gherkin
Scenario: Expired token redirects to login
Given Casey has an expired token stored in the browser
When Casey opens the rankings page and an API call returns 401
Then the token is removed from localStorage
And Casey is redirected to "/login"
```

```gherkin
Scenario: Failed login still shows an error
Given Casey is on the login page
When Casey submits invalid credentials and the API returns 401
Then an error message is shown on the login form
```
