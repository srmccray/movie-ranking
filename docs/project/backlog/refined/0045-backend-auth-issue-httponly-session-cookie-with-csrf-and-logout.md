---
id: '0045'
title: 'app/routers/auth.py + app/dependencies.py: issue an httpOnly session cookie
  with CSRF double-submit and add POST /auth/logout/'
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

# TASK-0045: app/routers/auth.py + app/dependencies.py: issue an httpOnly session cookie with CSRF double-submit and add POST /auth/logout/

## Summary
Backend half of ADR-0013. Login and register additionally set an httpOnly `session` cookie holding the same JWT and a readable `csrf_token` cookie; `get_current_user` accepts the cookie or the existing Bearer header; cookie-authenticated unsafe requests must carry a matching `X-CSRF-Token` header; a new logout endpoint clears both cookies. Existing clients keep working, so this ships before any frontend change.

Priority: P1. Size: M. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- Token issuance today: `app/routers/auth.py:30-67` (`register`, returns `Token(access_token=...)`, 201) and `:79-117` (`login`, OAuth2 password form, returns `Token`), both calling `create_access_token` (`app/utils/security.py:44`). Google sign-in is handled in TASK-0046.
- New helper module `app/utils/cookies.py`: `set_session_cookies(response, token)` sets `session` (`HttpOnly`, `Secure` unless `settings.DEBUG`, `SameSite=Lax`, `Path=/api`, `Max-Age=ACCESS_TOKEN_EXPIRE_MINUTES * 60`) and `csrf_token` (`secrets.token_urlsafe(32)`, not httpOnly, `Secure` unless DEBUG, `SameSite=Lax`, `Path=/`, same `Max-Age`); `clear_session_cookies(response)`. Both endpoints take `response: Response` and call it; the JSON body is unchanged (ADR-0013: bearer compatibility).
- `app/dependencies.py:12-50`: `oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")` raises 401 when the header is missing. Change it to `auto_error=False`; in `get_current_user(request, bearer_token, db)` use the header token if present (no CSRF check), otherwise the `session` cookie; if neither, 401 with the existing `Could not validate credentials` detail. For cookie-authenticated requests with method in `{POST, PUT, PATCH, DELETE}` require `X-CSRF-Token` equal to the `csrf_token` cookie (`hmac.compare_digest`), else `403 {"detail": "CSRF token missing or invalid"}`. Keep `OAuth2PasswordBearer` (or an `APIKeyHeader`-style scheme) registered so OpenAPI still documents the security scheme.
- `POST /api/v1/auth/logout/` (204, no authentication required, no CSRF required because it only clears state): clears both cookies. Add it to `app/routers/auth.py` (150 lines) or a new `auth_session.py` if the file approaches 300. Trailing slash per convention.
- CORS in `app/main.py` already sets `allow_credentials=True` with an explicit origin list; make sure `X-CSRF-Token` is allowed (`allow_headers=["*"]` today).
- Security review: run the `security-review` agent on the PR (project rule for auth changes).

## Notes and Risks
- Production is same-origin through CloudFront (`/api/*` behavior forwards all viewer headers including `Cookie`, cache disabled), so no CORS credential setup is needed there; local dev relies on the Vite proxy (`frontend/vite.config.ts:17`) staying same-origin.
- Do not log cookies or the CSRF header (see TASK-0037).
- `SameSite=Lax` still sends the cookie on top-level GET navigations, which the Google callback needs; the CSRF double-submit covers cross-site POST/PUT/PATCH/DELETE.
- The 24-hour token lifetime is unchanged; refresh tokens are out of scope (ADR-0013 clause 7).
- Existing tests authenticate with `Authorization: Bearer` (see `tests/conftest.py` `auth_headers`); they must pass unmodified. httpx's `AsyncClient` stores cookies automatically, so cookie tests need a client without the bearer header.

## Definition of Done
- [ ] `POST /api/v1/auth/login` and `/register` still return the same JSON body and now also `Set-Cookie: session=...; HttpOnly; Secure; SameSite=Lax; Path=/api` and a `csrf_token` cookie without `HttpOnly`.
- [ ] A request authenticated only by the `session` cookie succeeds on `GET /api/v1/auth/me/`; a `DELETE /api/v1/rankings/all/` with the cookie but without `X-CSRF-Token` returns 403 and deletes nothing; with the matching header it returns 204.
- [ ] Requests authenticated by the Bearer header behave exactly as before and need no CSRF header.
- [ ] `POST /api/v1/auth/logout/` returns 204 and expires both cookies; the following `GET /api/v1/auth/me/` returns 401.
- [ ] An invalid or expired cookie returns 401 (not 403) on safe and unsafe methods.
- [ ] `venv/bin/pytest` passes with the existing assertions; the `security-review` agent's findings are addressed.

```gherkin
Scenario: Cross-site requests cannot act as Casey
  Given Casey is signed in with a session cookie
  When a request DELETE /api/v1/rankings/all/ arrives with the cookie but without the X-CSRF-Token header
  Then the response is 403 and no rankings are deleted
```

## INVEST Criteria
- **Independent**: No task dependencies; executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Gives the browser a session the page's scripts cannot read; ADR-0013, PRD-0007 outcome 8, US-0010.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Medium: one PR touching several files; keep it under about 500 lines of changed source (excluding generated files and migrations' SQL boilerplate).
- **Testable**: Observable through headers and status codes of public endpoints (ADR-0003).
