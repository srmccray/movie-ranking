---
id: '0006'
title: "Catch regressions in CI before merge"
status: Accepted
created: 2026-10-14
persona: "Alex (The Systems Builder)"
target_bc: "core"
feature: "FEAT-CORE-06"
governing_prd: "PRD-0006"
scenarios:
  - "Type and lint errors fail the pull request"
  - "Migrations are exercised on PostgreSQL"
  - "API contract drift fails the pull request"
---

# US-0006 — Catch regressions in CI before merge

## Governing PRD
- [`PRD-0006: Platform Foundations`](../../product/accepted/prd-0006-platform-foundations.md)

## User Story

**As** Alex (The Systems Builder),
**I want** CI to run lint, type checks, PostgreSQL migrations and API contract checks on every pull request,
**So that** agent-authored changes cannot merge with type errors, broken migrations or frontend types that no longer match the backend.

## Acceptance Criteria

```gherkin
Scenario: Type and lint errors fail the pull request
  Given a pull request that introduces a TypeScript type error in frontend/src
  When the CI Quality Gate workflow runs
  Then the "Frontend Tests & Build" job fails at the `tsc -b` step
  And a pull request with only a lint error fails at the `npm run lint` step
```

```gherkin
Scenario: Migrations are exercised on PostgreSQL
  Given a pull request that adds an Alembic migration with invalid SQL
  When the CI Quality Gate workflow runs
  Then the PostgreSQL job fails at `alembic upgrade head`
  And the pull request cannot merge
```

```gherkin
Scenario: API contract drift fails the pull request
  Given a pull request that renames a field in a Pydantic response schema
  And frontend/src/api/schema.d.ts is not regenerated
  When the CI Quality Gate workflow runs
  Then the contract-drift check fails with a non-empty git diff
```
