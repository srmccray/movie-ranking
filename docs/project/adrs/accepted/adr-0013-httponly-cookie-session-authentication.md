---
id: ADR-0013
title: Browser Sessions Use httpOnly Cookies Instead of localStorage Bearer Tokens
status: Accepted
date: '2026-10-14'
---

# ADR-0013: Browser Sessions Use httpOnly Cookies Instead of localStorage Bearer Tokens

## Status
Accepted

## Context
- The JWT is stored in `localStorage` (`frontend/src/context/AuthContext.tsx:14-33`, key `movie_ranking_token`) and attached as `Authorization: Bearer` by `frontend/src/api/client.ts:46-48`. Any XSS can read it.
- The Google sign-in callback puts the JWT in the URL: `app/routers/google_auth/login.py:214-217` redirects to `{redirect_uri}?token=<jwt>`, which lands in browser history, server and CDN logs and Referer headers (`frontend/src/pages/GoogleCallbackPage.tsx:47` reads it back).
- `redirect_uri` is taken verbatim from the query string of `GET /api/v1/auth/google/login/` and stored in `oauth_states` without validation, so a crafted login flow can send a victim's token to an arbitrary origin.
- Production is same-origin: CloudFront serves the SPA and forwards `/api/*` (cache disabled, all viewer headers except Host) to API Gateway, so cookies reach the backend without CORS credentials in production.

## Decision
1. After register, login and the Google callback the backend sets the session as a **`session` cookie: `HttpOnly; Secure; SameSite=Lax; Path=/api`, `Max-Age` equal to the token lifetime**. The JWT format, lifetime (`ACCESS_TOKEN_EXPIRE_MINUTES`) and claims are unchanged. `Secure` is relaxed only when `DEBUG` is true (local HTTP).
2. `get_current_user` accepts the cookie **or** an `Authorization: Bearer` header (kept for tests, scripts and API clients). Requests authenticated by header are CSRF-exempt because browsers do not attach that header ambiently.
3. **CSRF**: for unsafe methods (POST, PUT, PATCH, DELETE) authenticated by cookie, the backend requires a double-submit token: a non-httpOnly `csrf_token` cookie (`Path=/`) is set with the session and its value must be echoed in an `X-CSRF-Token` header. `SameSite=Lax` plus this check covers cross-site POSTs; the Google callback is a top-level GET and works under Lax.
4. New `POST /api/v1/auth/logout/` clears both cookies. `GET /api/v1/auth/me/` is how the SPA learns whether it is signed in; the frontend stores no token.
5. **The Google callback never puts a credential in a URL**: it sets the cookies on the 302 response and redirects to a clean path. `redirect_uri` is validated against an allowlist (relative paths and the configured `CORS_ORIGIN`), so the open redirect is closed independently of this change (TASK-0028).
6. The Vite dev proxy keeps development same-origin, so no cross-origin credentials setup is needed. All `localStorage` token code is removed. The 401 handler (PRD-0003, US-0003) clears client auth state without touching `localStorage`, and the e2e helpers stop reading `movie_ranking_token`.
7. Refresh tokens, shorter lifetimes, token revocation and replacing python-jose with PyJWT are explicitly out of scope and tracked separately.

## Consequences
- **Positive**: XSS can no longer exfiltrate the session token; the token disappears from URLs and logs; the open redirect is closed.
- **Negative**: CSRF protection becomes our responsibility; the frontend, the e2e suite and the US-0003 scenario wording change; local development relies on the Vite proxy staying same-origin; tests need cookie-jar and header variants.
- **Compatibility**: bearer-header support and the `access_token` JSON field stay, so the migration ships in three steps (cookie issuance and CSRF, Google callback cookie with a temporary legacy `?token=` flag, then the frontend switch that also removes the legacy flag). A later decision can drop the JSON field once tests no longer use bearer fixtures.
