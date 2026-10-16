---
id: '0032'
title: 'deploy.yml: run alembic upgrade head before update-function-code and abort
  the deploy if it fails'
status: Refined
dependencies:
- TASK-0031
- TASK-0018
governing_adrs:
- ADR-0009
- ADR-0008
- ADR-0007
governing_prds:
- PRD-0007
governing_stories:
- US-0009
target_bc: infra
---

# TASK-0032: deploy.yml: run alembic upgrade head before update-function-code and abort the deploy if it fails

## Summary
`deploy.yml` has no migration step: schema changes are applied by hand and a code deploy can ship before its migration. Add an `alembic upgrade head` step that runs against the production database before `update-function-code`, so a failing migration stops the deploy and leaves the previous code running.

Priority: P1. Size: M. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- Insert after 'Configure AWS credentials (OIDC)' and before 'Package Lambda function' / 'Deploy Lambda function' in the `deploy` job: fetch `DATABASE_URL` with `aws ssm get-parameter --name /movie-ranking/prod/DATABASE_URL --with-decryption --query Parameter.Value --output text`, mask it (`echo "::add-mask::..."`), export it plus dummy `SECRET_KEY`/`TMDB_API_KEY` (needed because `alembic/env.py` imports `app.config.settings`), `pip install -r requirements.txt`, then `alembic upgrade head`.
- IAM: the deploy role (`movie-ranking-deploy`, stack lines ~283-340) needs `ssm:GetParameter` on `arn:aws:ssm:<region>:<account>:parameter/movie-ranking/prod/DATABASE_URL`. Add it in the stack.
- **Spike first (acceptance of the whole task)**: the database is an external PostgreSQL (`infra/CLAUDE.md`: no RDS in the stack) and its network rules are not recorded in the repo. Run `alembic current` from a `workflow_dispatch` run to prove GitHub-hosted runners can connect. If they cannot (IP allow-list), implement the ADR-0009 fallback instead: handle `{"action": "migrate"}` events in `lambda_handler.py` by running Alembic programmatically, ship `alembic/` and `alembic.ini` in the package (the packaging step copies only `app/` and `lambda_handler.py`, and `infra/CLAUDE.md` notes `alembic/` is not included; the CDK exclude list also names `alembic.ini`), and invoke it with `aws lambda invoke` before `update-function-code`; fail the job on a non-200 payload.
- Migrations must be backward compatible with the code that is still running while they apply (expand now, contract in a later release). Write that rule into `app/CLAUDE.md`'s migration guidance (the 'Migrations' table around line 875).

## Notes and Risks
- Destructive migrations (TASK-0024, TASK-0020) are applied by hand with a backup before this task lands; do not let the first automated run be one of them. Before enabling, run `alembic current` and `alembic heads` by hand and make sure production is at head.
- Concurrency: two overlapping deploys could run migrations concurrently; add `concurrency: group: deploy` to the workflow (TASK-0033 also needs it).
- The step runs on the runner, so `DATABASE_URL` is only in memory and masked in logs.

## Dependencies
- TASK-0031: both edit `.github/workflows/deploy.yml`; this one builds on the cleaned-up job.
- TASK-0018: migrations are only trusted in production once CI has proven the full chain on PostgreSQL.

## Definition of Done
- [ ] The spike result (runner can or cannot reach the database) is recorded in the PR and the chosen path (runner or Lambda-invoked) is implemented.
- [ ] A deploy with a new no-op migration applies it before the code is published (`alembic_version` advances, visible in the job log).
- [ ] A deploy whose migration raises an error fails at the migration step and the previously published Lambda version keeps serving (`GET /health` OK, version unchanged).
- [ ] The deploy role can read only the `DATABASE_URL` parameter, not the whole prefix.

```gherkin
Scenario: A failing migration stops the deploy
  Given a commit on main whose Alembic migration raises an error
  When the Deploy to AWS workflow runs
  Then the migration step fails
  And the previously published Lambda code stays in place
```

## INVEST Criteria
- **Independent**: Ordered after TASK-0031, TASK-0018 (see Dependencies); otherwise executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Schema and code ship together and a bad migration can no longer reach production code; ADR-0009, PRD-0007 outcome 3, US-0009.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Medium: one PR touching several files; keep it under about 500 lines of changed source (excluding generated files and migrations' SQL boilerplate).
- **Testable**: Observed by deploying a deliberately failing migration to a safe branch environment or by dry-running with `workflow_dispatch` (ADR-0004 CI loop).
