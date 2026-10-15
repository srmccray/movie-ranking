---
id: '0047'
title: 'frontend: switch auth to the cookie session, drop localStorage tokens, update e2e and US-0003, remove the legacy ?token= redirect'
status: Proposed
governing_adrs:
- ADR-0013
- ADR-0006
governing_prds:
- PRD-0007
governing_stories:
- US-0010
- US-0003
dependencies:
- TASK-0045
- TASK-0046
- TASK-0008
target_bc: frontend
priority: P1
---

# TASK-0047: frontend: switch auth to the cookie session, drop localStorage tokens, update e2e and US-0003, remove the legacy ?token= redirect

## Summary
Frontend half of ADR-0013: stop storing the JWT in `localStorage` and attaching `Authorization` headers; rely on the httpOnly cookie, send the CSRF header on unsafe requests, learn the signed-in state from `GET /auth/me/`, and call `POST /auth/logout/` on logout. Update the e2e suite and the US-0003 scenario that mention localStorage, and remove the legacy `?token=` redirect from the backend in the same PR.

Priority: P1. Size: M. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- `frontend/src/api/client.ts`: remove the `token` field and `setToken` (line 31) and both `Authorization` blocks (`request()` lines 46-48 and `uploadAmazonPrimeCSV` lines 209-211); add a small `getCsrfToken()` reading the `csrf_token` cookie from `document.cookie` and set `X-CSRF-Token` on non-GET requests (including the multipart upload). Same-origin `fetch` sends cookies by default (`credentials: 'same-origin'`; set it explicitly). Add `logout()` -> `POST /auth/logout/`.
- `frontend/src/context/AuthContext.tsx`: remove `TOKEN_KEY = 'movie_ranking_token'` and all `localStorage` use (lines 14-33, 67-69); on mount call `apiClient.getCurrentUser()` to set `isAuthenticated` (with a loading state so `ProtectedRoute` does not flash the login page); `login`/`register` just refresh the user after the API call; `logout` calls `apiClient.logout()` then clears state; the 401 handler (`setOnUnauthorized`, US-0003) clears state without touching storage. Remove `loginWithToken`.
- `frontend/src/pages/GoogleCallbackPage.tsx:46-60` reads `searchParams.get('token')` and calls `loginWithToken`; replace with: if no `error` param, call the auth refresh (`/auth/me/`) and navigate home, showing the existing error UI on failure.
- Tests to update: `src/api/client.test.ts` (assertions on `Authorization` at lines 149-170 become CSRF-header assertions), `src/context/AuthContext.test.tsx`, `src/pages/LoginPage.test.tsx`, `src/pages/GoogleCallbackPage.test.tsx`, MSW `handlers/auth.ts` (no longer require a Bearer header: key the mock on a `session` cookie or a test flag; `Set-Cookie` from mocked responses may not populate `document.cookie` in the test environment, so set `document.cookie = 'csrf_token=...'` directly in tests that need it), and `src/__tests__/setup.ts` (localStorage mock stays for other uses).
- e2e: `frontend/e2e/support/auth.ts:22-23` `readToken` reads `localStorage[TOKEN_KEY]`; replace with a helper that asserts the `session` cookie exists with `httpOnly` via `context.cookies()` and that `document.cookie` does not contain it. `frontend/e2e/smoke-auth.spec.ts:19,23` and `frontend/e2e/us-0003-auto-logout.spec.ts:2,16,31-32` set and read the localStorage token; change the expired-session setup to `context.addCookies([{ name: 'session', value: 'expired-or-invalid', httpOnly: true, ... }])` and the assertion to 'the session cookie is gone and the app is at /login'.
- Stories: rewrite the US-0003 scenario steps that say 'has an expired token stored in the browser' and 'the token is removed from localStorage' (`docs/project/user_stories/accepted/us-0003-automatically-log-out-on-expired-session.md`) to the cookie wording. (ADR-0005 forbids feature branches from touching `docs/project/backlog/` only; user stories are editable.)
- Backend (one small change in the same PR): in `app/routers/google_auth/login.py` delete the `?token=` branch and the `GOOGLE_LEGACY_TOKEN_IN_URL` setting added by TASK-0046, so the redirect is always the clean URL; update `app/CLAUDE.md:767` and `tests/test_google_auth_login.py` accordingly.
- Docs: `frontend/CLAUDE.md` and root `CLAUDE.md` authentication sections (token storage, 401 handling).

## Notes and Risks
- Deploy order is safe: `deploy.yml` syncs the frontend to S3 before publishing Lambda code, and the backend already sets cookies (from TASK-0045/TASK-0046), so the new frontend works against either backend version.
- Open sessions of users who signed in with the old build keep a `movie_ranking_token` in `localStorage`; the new app ignores it and shows the login page once. Add a one-time `localStorage.removeItem('movie_ranking_token')` on startup.
- ADR-0006 requires Playwright coverage of UI behavior; run `cd frontend && npm run test:e2e` locally and attach the result (Playwright is not yet in CI).

## Dependencies
- TASK-0045 and TASK-0046 must already be deployed: the frontend relies on the cookie being set by login, register and the Google callback.
- TASK-0008 fixes the `HeadersInit` typing in `src/api/client.ts` that this task rewrites, and makes `tsc -b` reliable for verifying the change.

## Definition of Done
- [ ] `grep -rn "localStorage\|movie_ranking_token\|Authorization" frontend/src --include=*.ts --include=*.tsx` shows no token storage or Authorization header in non-test source (a one-time cleanup of the old key is the only allowed mention).
- [ ] After password login in a real browser (Playwright), `context.cookies()` contains an httpOnly `session` cookie, `document.cookie` does not contain it, and the rankings page loads.
- [ ] `DELETE /rankings/all/` and other unsafe requests from the SPA carry `X-CSRF-Token` and succeed; the same call without it returns 403 (checked in e2e or a client test).
- [ ] Completing Google sign-in (UI half, with the backend fake from the e2e setup or a mocked callback in Vitest) never produces a URL containing `token=`, and `Location` from the backend callback has no token.
- [ ] The US-0003 e2e scenarios pass with cookie wording and the story file is updated.
- [ ] `npm run lint`, `npx tsc -b`, `npm run test:run`, `npm run test:e2e` and `venv/bin/pytest` pass; the `security-review` agent reviewed the combined cookie work.

```gherkin
Scenario: The session token is not readable by page scripts
  Given Casey signs in with email and password
  When Casey opens the browser console on the rankings page
  Then `document.cookie` does not contain the session token
  And localStorage has no "movie_ranking_token" entry
  And the rankings page still loads
```

## INVEST Criteria
- **Independent**: Ordered after TASK-0045, TASK-0046, TASK-0008 (see Dependencies); otherwise executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Removes the XSS-readable token and the token-in-URL path from the product; ADR-0013, PRD-0007 outcomes 8-9, US-0010 and US-0003.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Medium: one PR touching several files; keep it under about 500 lines of changed source (excluding generated files and migrations' SQL boilerplate).
- **Testable**: Playwright journeys through the real UI and backend (ADR-0006) plus Vitest and pytest suites (ADR-0003).
