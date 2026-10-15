---
id: '0033'
title: 'deploy.yml: trigger from a successful CI Quality Gate run and drop the duplicate test jobs'
status: Proposed
governing_adrs:
- ADR-0009
- ADR-0004
governing_prds:
- PRD-0007
governing_stories:
- US-0009
dependencies:
- TASK-0032
target_bc: infra
priority: P2
---

# TASK-0033: deploy.yml: trigger from a successful CI Quality Gate run and drop the duplicate test jobs

## Summary
`deploy.yml` starts on every push to `main` and runs its own `test-backend` (Python 3.12) and `test-frontend` jobs instead of waiting for the `CI Quality Gate (movie-ranking)` workflow, so a deploy can run while CI is red or unfinished. Make the deploy depend on a successful CI run for the same commit.

Priority: P2. Size: S. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- `.github/workflows/deploy.yml`: replace `on: push: branches: [main]` with `on: workflow_run: workflows: ["CI Quality Gate (movie-ranking)"], types: [completed], branches: [main]`, keep `workflow_dispatch`. The CI workflow name is the first line of `ci.yml`.
- Add `if: github.event_name == 'workflow_dispatch' || github.event.workflow_run.conclusion == 'success'` to the `deploy` job, and check out `ref: ${{ github.event.workflow_run.head_sha || github.sha }}` so the deployed commit is exactly the one CI validated (a `workflow_run` job otherwise checks out the default branch head).
- Delete the `test-backend` and `test-frontend` jobs and the `needs: [test-backend, test-frontend]` line. CI already runs backend tests, the PostgreSQL job (TASK-0018), lint, type-check and frontend tests.
- Add `concurrency: group: deploy-production, cancel-in-progress: false` so overlapping runs queue.
- OIDC: the role trust policy matches `repo:<repo>:*` (stack lines ~290-296), which covers `workflow_run` runs; confirm with a `workflow_dispatch` dry run that `aws-actions/configure-aws-credentials` still assumes the role.
- Optional alignment: `ci.yml`'s main pytest job runs Python 3.13 while Lambda runs 3.12; consider moving it to 3.12 so the gate tests the production interpreter (TASK-0018 already uses 3.12).

## Notes and Risks
- Behavior change: a push that only touches docs still triggers CI and then a deploy (as today). If that is unwanted, add `paths-ignore` to the CI trigger in a separate change.
- `workflow_run` always executes the workflow file from the default branch, so edits to `deploy.yml` on a PR do not take effect until merged; test with `workflow_dispatch`.

## Dependencies
- TASK-0032 also restructures the `deploy` job in `.github/workflows/deploy.yml`; apply the trigger change after it.

## Definition of Done
- [ ] Pushing a commit to `main` whose CI run fails does not start the deploy workflow's `deploy` job (shown as skipped).
- [ ] Pushing a green commit deploys the same SHA that CI tested (the job log shows the `head_sha` checkout).
- [ ] `deploy.yml` contains no `pytest` or `npm run test:run` steps.
- [ ] Two quick successive pushes deploy one after the other, never concurrently.

```gherkin
Scenario: A red CI run cannot deploy
  Given a commit on main whose CI Quality Gate run concluded with failure
  When the Deploy to AWS workflow is evaluated
  Then the deploy job does not run
```

## INVEST Criteria
- **Independent**: Ordered after TASK-0032 (see Dependencies); otherwise executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Removes the possibility of shipping a commit CI has rejected and the maintenance of two test definitions; ADR-0009, PRD-0007 outcome 2, US-0009.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Small: one focused PR, a few files, well under 500 lines of change.
- **Testable**: Workflow run results for a red and a green commit (ADR-0004).
