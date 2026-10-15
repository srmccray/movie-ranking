---
id: '0046'
title: 'app/routers/google_auth/login.py: set the session cookie on the Google callback
  redirect and gate the legacy ?token= parameter'
status: Refined
dependencies:
- TASK-0045
- TASK-0028
governing_adrs:
- ADR-0013
- ADR-0003
governing_prds:
- PRD-0007
governing_stories:
- US-0010
target_bc: backend
---

# TASK-0046: app/routers/google_auth/login.py: set the session cookie on the Google callback redirect and gate the legacy ?token= parameter

## Summary
The Google callback ends with `RedirectResponse(f"{custom_redirect_uri}?token={access_token}")` (`app/routers/google_auth/login.py:214-217`), putting the JWT in browser history, logs and Referer headers. Set the session cookies on that response so the frontend no longer needs the URL token, and keep the legacy parameter only behind a setting until the frontend switches (TASK-0047).

Priority: P1. Size: S. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- `login.py:211-219`: after `access_token = create_access_token(...)`: build the `RedirectResponse` (or the JSON `Token` response when no `redirect_uri` was stored), call `set_session_cookies(response, access_token)` on it.
- Add `GOOGLE_LEGACY_TOKEN_IN_URL: bool = True` to `app/config.py`. When true, keep appending `?token=` (current behavior, so the deployed frontend keeps working); when false, redirect to the clean URL. TASK-0047 flips the default to false and removes the legacy code in the same PR as the frontend change.
- The link flow (`app/routers/google_auth/link.py:41-118`) authenticates through `oauth_states.user_id` and never issues a token, so it needs no change.
- Document in `app/CLAUDE.md` (line 767 describes `?token=<jwt>`).

## Notes and Risks
- Both `Set-Cookie` headers must be present on the 302; verify with `httpx` `follow_redirects=False`.
- The cookie `Path=/api` is sent on the API calls the SPA makes after landing on the frontend route; the redirect target is a frontend path (for example `/auth/google/callback`), which does not need the cookie itself.
- Temporary flag, removed by TASK-0047; keep it out of `.env.example` docs except for a one-line comment.

## Dependencies
- TASK-0045 provides `set_session_cookies` and cookie-aware authentication.
- TASK-0028 guarantees the redirect target is our own origin before the cookie is attached to that redirect.

## Definition of Done
- [ ] A successful Google callback with a stored `redirect_uri` returns 302 with `Set-Cookie` for `session` (httpOnly) and `csrf_token`.
- [ ] With `GOOGLE_LEGACY_TOKEN_IN_URL=false` the `Location` header contains no `token=`; with the default `true` it still does.
- [ ] Without a stored `redirect_uri` the JSON `Token` response is unchanged and also sets the cookies.
- [ ] `tests/test_google_auth_login.py` and `tests/test_google_auth_accounts.py` pass.

```gherkin
Scenario: The Google callback sets the session cookie
  Given Casey completes Google consent and the state is valid
  When the callback redirects to the frontend
  Then the response sets an httpOnly session cookie
  And with the legacy flag off the redirect URL contains no token
```

## INVEST Criteria
- **Independent**: Ordered after TASK-0045, TASK-0028 (see Dependencies); otherwise executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Starts removing the credential from URLs without breaking the deployed frontend; ADR-0013, PRD-0007 outcome 9, US-0010.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Small: one focused PR, a few files, well under 500 lines of change.
- **Testable**: Status code, `Location` and `Set-Cookie` headers of the public callback (ADR-0003).
