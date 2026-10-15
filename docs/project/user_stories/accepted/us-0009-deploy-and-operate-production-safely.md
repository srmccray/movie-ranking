---
id: '0009'
title: "Deploy and operate production safely"
status: Accepted
created: 2026-10-14
persona: "Alex (The Systems Builder)"
target_bc: "infra"
feature: "FEAT-INFR-09"
governing_prd: "PRD-0007"
scenarios:
  - "A failing migration stops the deploy"
  - "Infrastructure deploys cannot wipe configuration"
  - "A failing request can be traced"
---

# US-0009 — Deploy and operate production safely

## Governing PRD
- [`PRD-0007: Operational Safety`](../../product/accepted/prd-0007-operational-safety.md)

## User Story

**As** Alex (The Systems Builder),
**I want** deploys that wait for CI, apply migrations first, keep secrets out of the function configuration and leave logs I can search by request,
**So that** a push to main cannot take production down and an outage can be diagnosed from CloudWatch alone.

## Acceptance Criteria

```gherkin
Scenario: A failing migration stops the deploy
  Given a commit on main whose Alembic migration raises an error
  When the Deploy to AWS workflow runs
  Then the migration step fails
  And the previously published Lambda code stays in place
```

```gherkin
Scenario: Infrastructure deploys cannot wipe configuration
  Given the API function reads its secrets from SSM Parameter Store
  When an approved `cdk deploy` runs
  Then GET /health?deep=true still returns 200
  And the function environment contains no secret values
```

```gherkin
Scenario: A failing request can be traced
  Given a request to the API that raises an unhandled exception
  When Alex searches CloudWatch Logs for the request id in the X-Request-ID response header
  Then exactly one JSON error entry with that request_id and the exception type is found
```
