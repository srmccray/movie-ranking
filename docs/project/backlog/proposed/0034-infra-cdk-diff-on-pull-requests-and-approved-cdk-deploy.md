---
id: '0034'
title: 'deploy.yml + infra: run cdk diff on PRs touching infra/ and an approval-gated cdk deploy that never replaces Lambda code'
status: Proposed
governing_adrs:
- ADR-0009
- ADR-0008
governing_prds:
- PRD-0007
governing_stories:
- US-0009
dependencies:
- TASK-0030
- TASK-0031
- TASK-0033
target_bc: infra
priority: P2
---

# TASK-0034: deploy.yml + infra: run cdk diff on PRs touching infra/ and an approval-gated cdk deploy that never replaces Lambda code

## Summary
Infrastructure is changed from a laptop with `cdk deploy`, and the stack's own code asset (`lambda.Code.fromAsset(path.join(__dirname, "../.."), ...)`, `movie-ranking-stack.ts:73-110`, no bundling) is the repository without installed dependencies, so a manual deploy replaces working code with a package that cannot import `fastapi`. Implement ADR-0009 clauses 3-4: the stack stops managing code, PRs show `cdk diff`, and merges to `main` run an approved `cdk deploy` before the application deploy.

Priority: P2. Size: M. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- **Stack**: change `ApiFunction` code to an inline placeholder (`lambda.Code.fromInline("def handler(event, context): raise RuntimeError('deployed code missing')")` with a `handler: "lambda_handler.handler"`-compatible stub, or a constant asset directory) and document that code is published by `deploy.yml`'s `update-function-code`. Remove the `exclude` list (lines 74-103) and update `infra/CLAUDE.md` 'Lambda deployment excludes' (about lines 353-371). The first deploy after this change replaces the running code with the placeholder once, so the pipeline must run the application deploy job right after the CDK job in the same workflow run (`needs`).
- **PR workflow** `.github/workflows/infra-diff.yml`: on `pull_request` with `paths: ['infra/**']`, assume a read-only role via OIDC, `npm ci` in `infra/`, `npx cdk diff` and write it to `$GITHUB_STEP_SUMMARY`. Needs a role (trust `repo:<repo>:pull_request`) with `sts:AssumeRole` on the CDK bootstrap lookup role, read-only.
- **Deploy job** in `deploy.yml`: new `infra` job before `deploy`, `environment: production` (configure a required reviewer in GitHub settings), `npx cdk deploy --require-approval never` (the environment approval is the gate). Use a separate role `movie-ranking-infra-deploy` whose trust policy is restricted to `repo:<repo>:environment:production` and whose only permission is `sts:AssumeRole` on the account's `cdk-*` bootstrap roles. Do not widen the existing `movie-ranking-deploy` role (that would let any workflow run grant itself infrastructure rights).
- Create the new role(s) once by hand with `cdk deploy` from a laptop (bootstrap problem), record the ARNs as repository secrets/variables.
- `cdk.json` writes output to `infra/.cdk.out` (`infra/CLAUDE.md` line 56); make sure `.gitignore` already covers it.

## Notes and Risks
- Verify the inferred hazard before relying on it: run `npx cdk diff` after changing the code property and confirm the Lambda `Code` changes; do not test by deploying to production.
- Staging is out of scope (ADR-0009 clause 5).
- GitHub environment reviewers and protected branches are repository settings made by hand; list them in the PR checklist.

## Dependencies
- TASK-0030: until placeholders are gone, any automated `cdk deploy` would reset production secrets.
- TASK-0031 and TASK-0033: all three edit `.github/workflows/deploy.yml`; this builds on the final job structure.

## Definition of Done
- [ ] A PR that changes `infra/lib/movie-ranking-stack.ts` shows a `cdk diff` summary in the Actions run.
- [ ] A merge to `main` with an infrastructure change pauses at the `production` environment approval and, once approved, runs `cdk deploy` and then the application deploy.
- [ ] After a `cdk deploy` for an unrelated change (for example a log retention edit) the API still serves `GET /health` with 200 without a manual redeploy of code.
- [ ] `movie-ranking-deploy` gained no CloudFormation/IAM permissions; the infra role can only assume the CDK bootstrap roles.
- [ ] `infra/CLAUDE.md` describes the pipeline and no longer tells readers to re-run the GitHub deploy after a manual CDK deploy.

```gherkin
Scenario: Infrastructure deploys cannot wipe configuration or code
  Given the API function reads its secrets from SSM Parameter Store and its code is published by the application deploy job
  When an approved `cdk deploy` runs
  Then GET /health returns 200
  And the function environment contains no secret values
```

## INVEST Criteria
- **Independent**: Ordered after TASK-0030, TASK-0031, TASK-0033 (see Dependencies); otherwise executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Infrastructure changes become reviewed, repeatable and safe; ADR-0009, PRD-0007 outcome 4, US-0009.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Medium: one PR touching several files; keep it under about 500 lines of changed source (excluding generated files and migrations' SQL boilerplate).
- **Testable**: Workflow runs plus a live health check after an infra-only deploy (ADR-0003, ADR-0004).
