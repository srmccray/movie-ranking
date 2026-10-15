---
id: 0028
title: 'app/routers/google_auth/login.py: reject redirect_uri values outside an allowlist'
status: Refined
governing_adrs:
- ADR-0013
- ADR-0003
governing_prds:
- PRD-0007
governing_stories:
- US-0010
target_bc: backend
---

# TASK-0028: app/routers/google_auth/login.py: reject redirect_uri values outside an allowlist

## Summary
`GET /api/v1/auth/google/login/` accepts any `redirect_uri` query value, stores it in `oauth_states`, and after a successful sign-in the callback redirects to `{redirect_uri}?token=<jwt>`. Anyone can craft a login flow whose redirect target is their own site and receive the victim's JWT. Close this open redirect now, independently of the larger cookie migration.

Priority: P1. Size: S. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- Parameter: `app/routers/google_auth/login.py:34-39` (`redirect_uri: str | None = Query(None, ...)`), passed unvalidated to `oauth._create_state_token(db, redirect_uri)` (line 62) which stores it (`app/routers/google_auth/oauth.py`, `OAuthState.redirect_uri` String(500)).
- Use sites: `login.py:~214-217` (`redirect_url = f"{custom_redirect_uri}?token={access_token}"` -> 302) and the link flow in `app/routers/google_auth/link.py` (`_handle_link_callback` receives `custom_redirect_uri`; check how it is used and apply the same rule). The frontend sends absolute URLs on its own origin: `${window.location.origin}/auth/google/callback` for sign-in (`frontend/src/api/client.ts:108-109`) and `${window.location.origin}/settings` for linking (`:115-116`). The allowlist must therefore accept the deployed origin and the local dev origin. The link flow also builds redirects from the stored value (`app/routers/google_auth/link.py:41-118`, e.g. the `?linked=success` redirect).
- Add `validate_redirect_uri(value: str | None) -> str | None` in `app/routers/google_auth/oauth.py` (or a small `redirects.py`): accept `None`; accept a same-site relative path starting with a single `/` (reject `//host`, backslashes and control characters); accept an absolute URL only when its scheme+host+port equals an entry in an allowlist built from the existing `CORS_ORIGIN` setting (`app/main.py:22-26` reads `os.environ["CORS_ORIGIN"]`) plus `http://localhost:3000` and the Vite dev origin when `DEBUG` is true. Anything else returns `400` with `detail="Invalid redirect_uri"` from the login and link initiation endpoints.
- Also re-validate when reading it back in the callback (defense in depth, the stored value is trusted data but cheap to check).

## Notes and Risks
- This does not remove the token from the URL; that is TASK-0046. It only guarantees the token can only go to our own origin.
- Check the frontend's actual `redirect_uri` value in `frontend/src/pages/LoginPage.tsx`/`SettingsPage.tsx` and in the e2e tests so legitimate flows keep working; update the MSW handler if it hard-codes one.
- Use `urllib.parse.urlsplit` and compare parsed components; do not use prefix string matching (`https://app.example.com.evil.net`).

## Definition of Done
- [ ] `GET /api/v1/auth/google/login/?redirect_uri=https://evil.example/` returns 400 and creates no `oauth_states` row.
- [ ] `redirect_uri=//evil.example`, `redirect_uri=https://movies.example.com.evil.net/` (with `CORS_ORIGIN=https://movies.example.com`) and `redirect_uri=javascript:alert(1)` all return 400.
- [ ] `redirect_uri=/auth/google/callback` and `redirect_uri=<CORS_ORIGIN>/auth/google/callback` are accepted and the existing flow tests in `tests/test_google_auth_login.py` and `tests/test_google_auth_accounts.py` pass.
- [ ] The link initiation endpoint applies the same rule.

```gherkin
Scenario: A foreign redirect_uri is rejected
  Given the configured CORS origin is https://movies.example.com
  When a client calls GET /api/v1/auth/google/login/ with redirect_uri=https://evil.example/
  Then the response status is 400
  And no OAuth state is stored
```

## INVEST Criteria
- **Independent**: No task dependencies; executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Closes a token-exfiltration path (open redirect carrying the JWT); PRD-0007 outcome 9, US-0010.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Small: one focused PR, a few files, well under 500 lines of change.
- **Testable**: Observable via the public login/link endpoints and status codes (ADR-0003); candidate for the security-review agent.
