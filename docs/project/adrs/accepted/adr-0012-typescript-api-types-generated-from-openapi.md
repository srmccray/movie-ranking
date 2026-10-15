---
id: ADR-0012
title: TypeScript API Types Are Generated from the FastAPI OpenAPI Schema
status: Accepted
date: '2026-10-14'
---

# ADR-0012: TypeScript API Types Are Generated from the FastAPI OpenAPI Schema

## Status
Accepted

## Context
Frontend request and response types in `frontend/src/types/index.ts` (303 lines) are hand-written, and the root `CLAUDE.md` devotes an "API Contract Verification" checklist to making them match `app/schemas/*.py` by eye. The trailing-slash convention is also enforced only by documentation. FastAPI already publishes the contract at `/openapi.json`. Contract drift is a runtime error, not a compile error.

## Decision
1. The backend OpenAPI document is the **single source of truth** for API shapes. It is exported offline by a script that imports `app.main:app` and writes `app.openapi()` to `frontend/openapi.json` (no running server, no database).
2. The frontend generates `frontend/src/api/.generated/schema.d.ts` with **openapi-typescript** from that file (`npm run generate:api`). Both files are committed. The output lives in a dot-prefixed directory on purpose: `spec-ops health` counts every `.ts` file toward the ADR-0002 limit but skips hidden directories (`is_excluded_path` in spec_ops), and a generated declaration file for 25 routes and 31 schemas will exceed 500 lines. The directory is added to the `ignores` list in `frontend/eslint.config.js` so generated code is not linted.
3. **CI fails on drift**: a job regenerates both files and runs `git diff --exit-code`; contributors fix drift by running the two generate commands and committing.
4. Hand-written types in `src/types/index.ts` are replaced incrementally by aliases to generated schema types (`components["schemas"]["RankingResponse"]`). `client.ts` keeps its current fetch wrapper; adopting `openapi-fetch` is optional and not part of this decision.
5. A backend test asserts every route under `/api/v1` ends with a trailing slash except the documented exceptions (`/auth/register`, `/auth/login`), and that every route declares a `response_model` or `status_code=204`.
6. This extends ADR-0003's blackbox posture (the contract is checked through a public artifact); it does not replace contract tests.

## Consequences
- **Positive**: A backend schema change that breaks the frontend fails at `tsc -b` in CI; the manual checklist can shrink; the trailing-slash rule becomes executable.
- **Negative**: Two committed generated files create merge noise on API changes; adds `openapi-typescript` as a frontend dev dependency; generated names (`HTTPValidationError`, FastAPI-flavoured schema names) need a thin alias layer.
