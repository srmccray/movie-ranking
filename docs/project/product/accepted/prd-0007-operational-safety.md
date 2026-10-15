---
id: '0007'
title: Operational Safety
status: Accepted
created: 2026-10-14
target_persona: Alex (The Systems Builder)
component: infra
---

# PRD-0007 — Operational Safety

## Who this is for

- **Alex (The Systems Builder)**: deploys and operates the production stack (Lambda, API Gateway, CloudFront, external PostgreSQL) and needs deploys that cannot silently break production and failures that can be diagnosed.
- **Casey (The Movie Enthusiast)**: needs the session token to be protected from scripts, URLs and brute-force guessing.

## What the person cannot do today

- **Deploy safely.** Secrets sit in plaintext in the Lambda environment; `cdk deploy` resets `DATABASE_URL`, `SECRET_KEY` and `TMDB_API_KEY` to placeholders (`infra/lib/movie-ranking-stack.ts:110-115`); `deploy.yml` re-runs its own tests instead of waiting for CI, never runs migrations, and merges secrets into the function environment on every push to `main`. Infrastructure changes are made by hand.
- **Diagnose problems.** Logs are plain text from `logging.basicConfig` with no request id and no unhandled-exception handler; `/health` returns a static body without touching the database; the Lambda has no log retention, alarms or tracing.
- **Resist abuse.** `POST /api/v1/auth/login` and `/register` are unthrottled (bcrypt cost 12 on a 256 MB Lambda), and no concurrency cap protects the database from a spike.
- **Protect sign-in.** The JWT lives in `localStorage` (readable by any XSS), the Google callback redirects to `{redirect_uri}?token=<jwt>` (`app/routers/google_auth/login.py:214-217`), and `redirect_uri` is accepted without validation.
- **Reproduce builds.** `requirements.txt` uses open `>=` ranges and there is no lock file, no dependency scanning and no Dependabot; `docs/project/compliance/licenses.json` lists 8 of the 14 runtime packages.

## What good looks like

1. **Safe deploys (ADR-0008, ADR-0009)**: secrets in SSM, migrations applied automatically before new code is published, deploys gated on green CI, infrastructure changes reviewed through `cdk diff` and an approved `cdk deploy`.
2. **Observable service**: structured JSON logs with a request id, an exception handler that logs unhandled errors, a database-checking readiness probe, alarms on errors and throttles.
3. **Abuse limits**: API Gateway throttling and a Lambda concurrency cap, plus a per-IP rate rule on the auth paths.
4. **Protected sessions (ADR-0013)**: httpOnly cookie sessions with CSRF protection, no credential in any URL, and a validated Google `redirect_uri`.
5. **Reproducible, scanned dependencies**: pinned Python requirements used by CI and the Lambda build, Dependabot, and vulnerability scans in CI.

## What this does not do

- No staging environment (recorded as out of scope in ADR-0009), no refresh tokens or token revocation, no JWT library swap, no Lambda memory or connection-pool tuning (needs the observability work first), no CORS tightening or `/docs` gating.

## Checkable Outcomes

1. `aws lambda get-function-configuration` for the API function shows no `SECRET_KEY`, `DATABASE_URL`, `TMDB_API_KEY`, `GOOGLE_CLIENT_ID` or `GOOGLE_CLIENT_SECRET` in `Environment.Variables`, and the API still serves `GET /health` with 200.
2. `.github/workflows/deploy.yml` contains no `update-function-configuration` step and does not start unless the `CI Quality Gate` run for the same commit concluded `success`.
3. A deploy whose migration fails leaves the previously published Lambda code in place (the `update-function-code` step is not reached).
4. A pull request that changes `infra/**` shows a `cdk diff` summary, and `cdk deploy` on `main` waits for approval in the `production` environment.
5. Each request produces one JSON log line containing `request_id`, `method`, `path`, `status` and `duration_ms`, and the response carries the same id in `X-Request-ID`.
6. `GET /health?deep=true` returns 503 with `{"status": "unhealthy"}` when the database is unreachable and 200 otherwise.
7. Exceeding the configured request rate on `POST /api/v1/auth/login` from one IP returns HTTP 429 or 403 from the edge, not from the application.
8. After login, `document.cookie` in the browser does not contain the session token, `localStorage` contains no `movie_ranking_token`, and a `DELETE /api/v1/rankings/{id}/` sent with the cookie but without `X-CSRF-Token` returns 403.
9. Completing Google sign-in never navigates to a URL containing `token=`, and `GET /api/v1/auth/google/login/?redirect_uri=https://evil.example/` returns 400.
10. `pip install -r requirements.txt` installs only exact pinned versions, and CI fails on a known-vulnerable pinned package.

## Linked User Stories

- [US-0009: Deploy and operate production safely](../../user_stories/accepted/us-0009-deploy-and-operate-production-safely.md)
- [US-0010: Keep sign-in credentials out of scripts and URLs](../../user_stories/accepted/us-0010-keep-sign-in-credentials-out-of-scripts-and-urls.md)

## Implementing Backlog Tasks

- TASK-0028 (Google redirect allowlist)
- TASK-0029, TASK-0030, TASK-0031 (secrets in SSM, ADR-0008)
- TASK-0032, TASK-0033, TASK-0034 (deploy pipeline, ADR-0009)
- TASK-0035, TASK-0036 (throttling, concurrency cap and per-IP rate rule)
- TASK-0037, TASK-0038, TASK-0039 (observability)
- TASK-0040, TASK-0041 (dependency pinning and scanning)
- TASK-0045, TASK-0046, TASK-0047 (cookie sessions, ADR-0013)
