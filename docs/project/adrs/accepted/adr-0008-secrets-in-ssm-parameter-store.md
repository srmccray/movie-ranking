---
id: ADR-0008
title: Application Secrets Live in SSM Parameter Store, Not Lambda Environment Variables
status: Accepted
date: '2026-10-14'
---

# ADR-0008: Application Secrets Live in SSM Parameter Store, Not Lambda Environment Variables

## Status
Accepted

## Context
Secrets are currently handled in three overlapping ways:
- `infra/lib/movie-ranking-stack.ts` (lines 110-115) declares placeholder values for `DATABASE_URL`, `SECRET_KEY` and `TMDB_API_KEY` in the Lambda `environment`.
- `.github/workflows/deploy.yml` ("Update Lambda environment variables") reads the live environment, merges `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `SECRET_KEY` and `GOOGLE_REDIRECT_URI` from GitHub secrets, and writes it back on every deploy. `DATABASE_URL` and `TMDB_API_KEY` are set by hand.
- Consequently any `cdk deploy` resets the function to placeholders (documented in `infra/CLAUDE.md` as a manual recovery step), and every secret sits in plaintext in the Lambda configuration, readable with `lambda:GetFunctionConfiguration`.

This also blocks automating infrastructure deploys (ADR-0009), because the stack and the workflow both claim ownership of the same environment map.

## Decision
1. Secrets are stored as **SSM Parameter Store SecureString** parameters under a single prefix, `/movie-ranking/prod/` (names match the `Settings` fields: `DATABASE_URL`, `SECRET_KEY`, `TMDB_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`). Standard-tier parameters are free; Secrets Manager is not used because rotation is not needed and it costs per secret.
2. The CDK stack does **not** create or hold secret values (CloudFormation cannot resolve a SecureString into a Lambda environment, and values placed in templates end up in state). It creates the Lambda with only non-secret configuration (`CORS_ORIGIN`, `SSM_PARAMETER_PREFIX`, `GOOGLE_REDIRECT_URI`) and grants the function `ssm:GetParametersByPath` on the prefix plus `kms:Decrypt` through the default `aws/ssm` key.
3. The application loads parameters **once per cold start** (a pydantic-settings source in `app/config.py`, using `boto3`, which the Lambda Python runtime provides) and caches them in the module-level `settings` object. Environment variables and `.env` keep working and take precedence, so local development, tests and Docker are unchanged. When `SSM_PARAMETER_PREFIX` is unset, SSM is never contacted.
4. Parameter values are created and rotated with `aws ssm put-parameter --overwrite` (documented in `infra/CLAUDE.md`), never by CI. The deploy role loses `lambda:UpdateFunctionConfiguration` once the env-merge step is removed.

## Consequences
- **Positive**: `cdk deploy` can no longer wipe production configuration; secrets are encrypted at rest and not visible in Lambda configuration or CloudFormation; the deploy role gets narrower.
- **Negative**: One extra network call per cold start (roughly 20-50 ms); a mistyped parameter name fails at cold start, so the loader must raise a clear error naming the missing parameter; the first rollout needs a manual one-time `put-parameter` step before the stack change is deployed.
- **Rollback**: setting environment variables directly on the function keeps working because environment variables take precedence.
