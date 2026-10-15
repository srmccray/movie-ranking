---
id: '0035'
title: 'infra/lib/movie-ranking-stack.ts: throttle auth routes at API Gateway and cap Lambda concurrency'
status: Proposed
governing_adrs:
- ADR-0008
- ADR-0009
governing_prds:
- PRD-0007
governing_stories:
- US-0010
dependencies:
- TASK-0030
target_bc: infra
priority: P1
---

# TASK-0035: infra/lib/movie-ranking-stack.ts: throttle auth routes at API Gateway and cap Lambda concurrency

## Summary
`POST /api/v1/auth/login` and `/register` are unthrottled, and every login runs bcrypt (cost 12, `app/utils/security.py`) in the async handler on a 256 MB Lambda; a burst can also exhaust database connections because `NullPool` opens one connection per invocation (`app/database.py:40-45`). Add API Gateway throttling for the auth routes and a reserved concurrency cap.

Priority: P1. Size: S. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- Routes today: `HttpApi` with `/{proxy+}` ANY and `/` ANY (`movie-ranking-stack.ts:140-151`); a stage can only throttle by route key, so add explicit routes for the auth paths that point to the same Lambda integration: `POST /api/v1/auth/login`, `POST /api/v1/auth/register`, `GET /api/v1/auth/google/login/`, `GET /api/v1/auth/google/callback/` (note login and register have no trailing slash, the documented exception).
- Throttle through the default stage's L1 resource: `(this.httpApi.defaultStage!.node.defaultChild as apigatewayv2.CfnStage).routeSettings = { "POST /api/v1/auth/login": { throttlingRateLimit: 5, throttlingBurstLimit: 10 }, "POST /api/v1/auth/register": { throttlingRateLimit: 2, throttlingBurstLimit: 5 }, ... }` and `defaultRouteSettings = { throttlingRateLimit: 100, throttlingBurstLimit: 200 }`. Starting values are suggestions; adjust to measured traffic.
- Concurrency cap: `reservedConcurrentExecutions` on `ApiFunction` (suggest 10), chosen at or below the external PostgreSQL's `max_connections` minus admin headroom (look it up and record it in `infra/CLAUDE.md`). **Check the account quota first**: `aws lambda get-account-settings`; AWS requires at least 100 unreserved concurrent executions, so a low account limit (new accounts often start at 10) makes a reservation impossible. If so, skip the cap and record why.
- These limits are per route across all clients (API Gateway HTTP API cannot throttle per IP); the per-IP rule is TASK-0036.
- Document the limits and how to raise them in `infra/CLAUDE.md`.

## Notes and Risks
- Throttled requests receive HTTP 429 from API Gateway before reaching Lambda; the frontend `ApiClient` surfaces non-2xx as an error, so a throttled login shows the generic error. A friendlier message is a separate frontend task.
- Too-low limits turn an attack into a lockout for real users; keep generous values until TASK-0037 metrics show the real rate.
- Moving bcrypt to a thread pool (`run_in_threadpool`) is a separate backend improvement, not part of this task.

## Dependencies
- TASK-0030: any `cdk deploy` before the placeholder secrets are removed resets production configuration.

## Definition of Done
- [ ] `cdk diff` shows the explicit auth routes, `RouteSettings` for them and (if the account allows) `ReservedConcurrentExecutions`.
- [ ] Sending more than the burst limit of `POST /api/v1/auth/login` requests within a second to the deployed API returns HTTP 429 for the excess requests, and a normal login still succeeds afterwards.
- [ ] Existing routes keep working (`GET /health`, rankings, Google callback) and the Google sign-in flow completes.
- [ ] The reserved concurrency value (or the reason for omitting it) and the database `max_connections` are recorded in `infra/CLAUDE.md`.

```gherkin
Scenario: Login bursts are throttled at the edge of the API
  Given the login route has a burst limit of 10
  When a client sends 30 login requests within one second
  Then the excess requests receive HTTP 429 from API Gateway
  And a single later login request succeeds
```

## INVEST Criteria
- **Independent**: Ordered after TASK-0030 (see Dependencies); otherwise executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Limits CPU and database exhaustion from request floods; PRD-0007 outcome 7, US-0010.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Small: one focused PR, a few files, well under 500 lines of change.
- **Testable**: Observable HTTP responses from the deployed API (ADR-0003); can be checked with a short script against the production or a scratch stack.
