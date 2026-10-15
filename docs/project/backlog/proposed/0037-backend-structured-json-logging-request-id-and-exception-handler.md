---
id: '0037'
title: 'app/main.py: JSON logs with request ids, access logging and an unhandled-exception handler'
status: Proposed
governing_adrs:
- ADR-0003
- ADR-0002
governing_prds:
- PRD-0007
governing_stories:
- US-0009
dependencies: []
target_bc: backend
priority: P1
---

# TASK-0037: app/main.py: JSON logs with request ids, access logging and an unhandled-exception handler

## Summary
Logging is `logging.basicConfig(level=...)` plain text (`app/main.py:14`) with f-string messages, no request correlation, no access log, and no handler for unhandled exceptions, so a 500 leaves only a Lambda traceback with nothing to link it to the request. Add JSON logging, a request-id middleware and an exception handler that logs every unhandled error once.

Priority: P1. Size: M. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- New package `app/observability/` (keep `app/main.py` small): `logging_config.py` (a stdlib `logging.Formatter` that emits one JSON object per line with `timestamp`, `level`, `logger`, `message`, `request_id` and any `extra` fields; no new dependency; use `contextvars.ContextVar` for the request id), and `middleware.py`.
- Middleware (pure ASGI or `BaseHTTPMiddleware`): take `X-Request-ID` from the request if it is a valid UUID/short token, otherwise generate one (on Lambda, API Gateway's `x-amzn-requestid`/`requestContext.requestId` can be used when present); set the context var; add `X-Request-ID` to the response; after the response log one line: `method`, `path` (no query string, which may contain OAuth `code`/`state`), `status`, `duration_ms`, `user_id` when available.
- Exception handler: `@app.exception_handler(Exception)` logs `logger.exception("unhandled_exception", extra={...})` once and returns the existing 500 JSON shape (`{"detail": "Internal server error"}`) with the `X-Request-ID` header. `HTTPException` and validation errors keep FastAPI's default handlers.
- Wire it in `app/main.py` replacing `logging.basicConfig` (line 14). Mangum runs the same app, so Lambda gets the same logs; CloudWatch Logs Insights can then query `request_id`. Reduce noise: uvicorn access logs are not used on Lambda.
- Never log request bodies, `Authorization`/`Cookie` headers, tokens, or full URLs with query strings (this matters for TASK-0045). Add a small redaction test.
- Docs: `app/CLAUDE.md` logging section; add a CloudWatch Logs Insights example query to `infra/CLAUDE.md`.

## Notes and Risks
- Tests build their own FastAPI app in `tests/conftest.py:152-175` instead of importing `app.main`; add the middleware and handler to a shared `install_observability(app)` function and call it from the fixture so the behavior is tested through the public endpoints (ADR-0003).
- Keep existing `logger.info(f"...")` calls working; converting them all to structured fields is out of scope.
- Optional: AWS Lambda Powertools provides the same features but adds a dependency; the stdlib approach is chosen to avoid dependency and licence work.

## Definition of Done
- [ ] Every API response carries `X-Request-ID`; a request sending a valid `X-Request-ID` gets the same value back.
- [ ] A test that triggers an unhandled exception (a test-only route or a patched dependency at the HTTP boundary) receives a 500 JSON body and the captured log contains exactly one `unhandled_exception` record with the same `request_id` and the exception type.
- [ ] Each request emits one JSON access log record containing `request_id`, `method`, `path`, `status` and `duration_ms`, and the record never contains the query string, `Authorization` header or request body.
- [ ] `venv/bin/pytest` passes; new files are under 400 lines.

```gherkin
Scenario: A failing request can be traced
  Given a request to the API that raises an unhandled exception
  When Alex searches the logs for the request id in the X-Request-ID response header
  Then exactly one JSON error entry with that request_id and the exception type is found
```

## INVEST Criteria
- **Independent**: No task dependencies; executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Makes production failures diagnosable and is the prerequisite for tuning performance; PRD-0007 outcome 5, US-0009.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Medium: one PR touching several files; keep it under about 500 lines of changed source (excluding generated files and migrations' SQL boilerplate).
- **Testable**: Response headers and captured log records through public endpoints (ADR-0003).
