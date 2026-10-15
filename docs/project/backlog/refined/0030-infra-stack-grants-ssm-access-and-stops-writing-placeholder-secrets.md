---
id: '0030'
title: 'infra/lib/movie-ranking-stack.ts: grant the Lambda SSM read access and remove
  placeholder secret environment variables'
status: Refined
dependencies:
- TASK-0029
governing_adrs:
- ADR-0008
governing_prds:
- PRD-0007
governing_stories:
- US-0009
target_bc: infra
---

# TASK-0030: infra/lib/movie-ranking-stack.ts: grant the Lambda SSM read access and remove placeholder secret environment variables

## Summary
The CDK stack sets placeholder `DATABASE_URL`, `SECRET_KEY` and `TMDB_API_KEY` values (`infra/lib/movie-ranking-stack.ts:110-115`), so every `cdk deploy` wipes the real values. Switch the stack to non-secret configuration plus an IAM grant to read the SSM prefix, and document the one-time parameter creation.

Priority: P1. Size: S. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- Edit the `environment` block of `ApiFunction` (`movie-ranking-stack.ts:110-116`): remove `DATABASE_URL`, `SECRET_KEY`, `TMDB_API_KEY`; keep `CORS_ORIGIN: https://${domainName}`; add `SSM_PARAMETER_PREFIX: "/movie-ranking/prod/"` and `GOOGLE_REDIRECT_URI: https://${domainName}/api/v1/auth/google/callback/` (today hard-coded in `.github/workflows/deploy.yml` as `https://movies.stephenmccray.com/api/v1/auth/google/callback/`; derive it from the same `domainName` variable the stack already uses for `CORS_ORIGIN`).
- Grant read access: `this.lambdaFunction.addToRolePolicy(new iam.PolicyStatement({ actions: ["ssm:GetParametersByPath", "ssm:GetParameters"], resources: [`arn:aws:ssm:${this.region}:${this.account}:parameter/movie-ranking/prod`, `arn:aws:ssm:${this.region}:${this.account}:parameter/movie-ranking/prod/*`] }))`. SecureStrings encrypted with the AWS-managed `aws/ssm` key need no extra KMS statement (the key policy allows account principals via SSM); if a customer-managed key is used, add `kms:Decrypt` on it.
- Do not create the parameters in CDK (ADR-0008 clause 2). Add a 'Secrets' section to `infra/CLAUDE.md` replacing the 'Lambda Environment Variables' table (about lines 220-250 and 324-336) with the `aws ssm put-parameter --type SecureString --overwrite` commands for the five names and the cut-over order below. Remove the warning that `cdk deploy` resets the environment.
- Cut-over runbook (write it in the PR description and `infra/CLAUDE.md`): (1) read the current values from the Lambda configuration and GitHub secrets; (2) `put-parameter` all five as SecureString; (3) deploy the TASK-0029 release; (4) verify `GET /health` and a login; (5) `cdk deploy` this change; (6) re-verify. Rollback: `aws lambda update-function-configuration` with the old variables; the application prefers environment variables over SSM.

## Notes and Risks
- Between step 5 and the removal of the env-merge step in TASK-0031, a GitHub deploy would re-add `SECRET_KEY`/`GOOGLE_*` to the environment (they would win over SSM). Land TASK-0031 immediately after.
- A manual `cdk deploy` still uploads a code asset without installed dependencies (`infra/CLAUDE.md` says the CDK `code:` asset is only what a manual deploy uploads); after step 5 run the GitHub deploy workflow (`workflow_dispatch`) to republish the real package. TASK-0034 removes this hazard.
- Use `cdk diff` first and confirm only the environment block, the IAM policy and (if unchanged) nothing else differs.

## Dependencies
- TASK-0029 must be deployed first: the application must be able to read SSM before the environment variables disappear.

## Definition of Done
- [ ] `npx cdk diff` shows only the removed environment variables, the new `SSM_PARAMETER_PREFIX`/`GOOGLE_REDIRECT_URI` and one added IAM policy statement.
- [ ] After the documented cut-over, `aws lambda get-function-configuration --function-name movie-ranking-api --query 'Environment.Variables'` contains none of the five secret names, and `GET /health` returns 200 and a password login succeeds.
- [ ] `infra/CLAUDE.md` documents the SSM parameters and no longer says `cdk deploy` resets secrets.
- [ ] A second `cdk deploy` with no changes leaves the application working (no placeholder resets).

```gherkin
Scenario: A CDK deploy no longer wipes configuration
  Given the API function reads its secrets from SSM Parameter Store
  When `cdk deploy` runs for an unrelated infrastructure change
  Then GET /health still returns 200
  And the function environment contains no secret values
```

## INVEST Criteria
- **Independent**: Ordered after TASK-0029 (see Dependencies); otherwise executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Removes the placeholder-reset outage hazard and plaintext secrets in Lambda configuration; ADR-0008, PRD-0007 outcome 1, US-0009.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Small: one focused PR, a few files, well under 500 lines of change.
- **Testable**: Verified through `cdk diff` output, the Lambda configuration query and public health/login endpoints (ADR-0003).
