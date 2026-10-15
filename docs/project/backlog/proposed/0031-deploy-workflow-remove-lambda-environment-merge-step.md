---
id: '0031'
title: 'deploy.yml + infra stack: remove the ''Update Lambda environment variables'' step and the UpdateFunctionConfiguration permission'
status: Proposed
governing_adrs:
- ADR-0008
- ADR-0009
governing_prds:
- PRD-0007
governing_stories:
- US-0009
dependencies:
- TASK-0030
target_bc: infra
priority: P1
---

# TASK-0031: deploy.yml + infra stack: remove the 'Update Lambda environment variables' step and the UpdateFunctionConfiguration permission

## Summary
On every push to `main`, `.github/workflows/deploy.yml` reads the live Lambda environment, merges `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `SECRET_KEY` and `GOOGLE_REDIRECT_URI` from GitHub secrets, and writes it back (step 'Update Lambda environment variables'). Delete that step and the IAM permission it needs.

Priority: P1. Size: XS. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- `.github/workflows/deploy.yml`: delete the step named `Update Lambda environment variables` (it follows `Wait for Lambda update to complete`; roughly 30 lines using `aws lambda get-function-configuration`, `jq` and `aws lambda update-function-configuration`).
- `infra/lib/movie-ranking-stack.ts:~333` (deploy role policy statement 'Lambda update permission'): remove `lambda:UpdateFunctionConfiguration`; keep `UpdateFunctionCode`, `GetFunction`, `GetFunctionConfiguration` (the `aws lambda wait function-updated` step needs the read permissions). This needs a `cdk deploy`; until TASK-0034 lands that is a manual step, so note it in the PR.
- Docs: `infra/CLAUDE.md` deployment steps list ('Merge secrets into existing environment variables', about line 275) and the 'Required GitHub Secrets' table (rows for `SECRET_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`): remove them. After the first successful deploy without the step, delete those three repository secrets in GitHub (manual).

## Notes and Risks
- Order of operations matters: do not merge before the SSM cut-over in TASK-0030 is verified in production, or the next deploy leaves the function without `SECRET_KEY`/`GOOGLE_*`.
- Rollback is a revert of this PR plus re-adding the permission.

## Dependencies
- TASK-0030 makes SSM the source of all five secrets; only then is the merge step redundant.

## Definition of Done
- [ ] `.github/workflows/deploy.yml` contains no `update-function-configuration` call and no reference to `secrets.SECRET_KEY`, `secrets.GOOGLE_CLIENT_ID` or `secrets.GOOGLE_CLIENT_SECRET`.
- [ ] A deploy from `main` after this change completes and `GET /health` and Google sign-in still work.
- [ ] `lambda:UpdateFunctionConfiguration` is absent from the deploy role in the synthesized template.
- [ ] `infra/CLAUDE.md` no longer documents the env-merge step or the three GitHub secrets.

```gherkin
Scenario: Deploys no longer touch function configuration
  Given secrets live in SSM Parameter Store
  When a commit is deployed from main
  Then the deploy workflow updates only the function code
  And the function environment is unchanged
```

## INVEST Criteria
- **Independent**: Ordered after TASK-0030 (see Dependencies); otherwise executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Eliminates the second owner of Lambda configuration and shrinks the deploy role; PRD-0007 outcome 2, US-0009.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Extra small: a handful of lines in one or two files.
- **Testable**: Workflow definition inspected plus a real deploy; function configuration compared before and after (ADR-0003 black-box on the deployed system).
