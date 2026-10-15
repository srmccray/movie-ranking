---
id: ADR-0009
title: CI-Gated Deploys with Automated Migrations and Infrastructure in the Pipeline
status: Accepted
date: '2026-10-14'
---

# ADR-0009: CI-Gated Deploys with Automated Migrations and Infrastructure in the Pipeline

## Status
Accepted

## Context
`.github/workflows/deploy.yml` runs on every push to `main` and:
- re-runs its own copy of the tests (Python 3.12, `pytest tests/ -v`) instead of depending on the `CI Quality Gate` workflow (`ci.yml`, Python 3.13), so a deploy can start while CI is red or still running;
- has no database migration step, so schema changes are applied by hand and a code deploy can ship before its migration;
- never runs `cdk diff` or `cdk deploy`; infrastructure is changed from a laptop;
- publishes the Lambda from a Docker-built zip (`aws lambda update-function-code`), while the CDK stack (`infra/lib/movie-ranking-stack.ts`, `lambda.Code.fromAsset(path.join(__dirname, "../.."), ...)` with no bundling step) would deploy the raw repository without installed dependencies. A `cdk deploy` therefore replaces a working function with one that cannot import `fastapi`.

## Decision
1. **One test gate.** `deploy.yml` is triggered by `workflow_run` of `CI Quality Gate` with `conclusion == 'success'` on `main` (plus manual `workflow_dispatch`), and its duplicate test jobs are removed.
2. **Migrations run in the deploy job, before the new code is published**, using `alembic upgrade head` with the production `DATABASE_URL` read from SSM (ADR-0008) via the OIDC deploy role. Migrations must therefore be backward compatible with the currently running code (expand first, contract in a later release). If a migration fails, the code is not published. This assumes the database accepts connections from GitHub-hosted runners; if it does not, the fallback is a `migrate` event handled by the Lambda itself (invoked with `aws lambda invoke` before `update-function-code`), which requires shipping `alembic/` and `alembic.ini` in the package.
3. **One code path for the function package.** The Docker-built `lambda.zip` produced by the deploy job is the only artifact that ever becomes function code. The CDK stack stops bundling the repository: it creates the function from a minimal inline placeholder and treats code as externally managed, so `cdk deploy` never changes running code.
4. **Infrastructure goes through the pipeline.** Pull requests that touch `infra/**` run `cdk diff` and publish it as a job summary; after merge, a `cdk deploy` job runs in a GitHub `production` environment with a required reviewer, before the application deploy job.
5. **Staging is deliberately out of scope.** A second stack and database is revisited when there is a second maintainer or a risky migration; no `stage` parameterisation is added now.

## Consequences
- **Positive**: A red CI run cannot deploy; schema and code move together; infrastructure drift ends; deploys stop depending on remembering manual steps.
- **Negative**: Slightly slower deploys (waits for CI); expand/contract discipline is required for destructive migrations; the first run of the migration step needs the database reachable from runners (open question recorded in TASK-0032).
- **Depends on**: ADR-0008 (secrets must not live in the function configuration before `cdk deploy` is automated) and ADR-0007 (migrations are exercised in CI before reaching production).
