---
id: '0043'
title: 'frontend: generate API types with openapi-typescript and fail CI when they drift from the backend'
status: Proposed
governing_adrs:
- ADR-0012
- ADR-0002
governing_prds:
- PRD-0006
governing_stories:
- US-0006
dependencies:
- TASK-0042
- TASK-0009
target_bc: frontend
priority: P2
---

# TASK-0043: frontend: generate API types with openapi-typescript and fail CI when they drift from the backend

## Summary
Frontend types in `frontend/src/types/index.ts` (303 lines) are copied by hand from `app/schemas/*.py` and the root `CLAUDE.md` asks contributors to check them manually. Generate a TypeScript declaration file from the exported OpenAPI document, commit it, and add a CI job that fails if it is stale.

Priority: P2. Size: M. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- Add `openapi-typescript` (pin an exact 7.x version) to `frontend/package.json` devDependencies and scripts: `"generate:api": "openapi-typescript openapi.json -o src/api/.generated/schema.d.ts"`. Commit `frontend/openapi.json` (from TASK-0042) and `frontend/src/api/.generated/schema.d.ts`. The dot-prefixed directory is deliberate: `spec-ops health` counts every `.ts` file toward the 500-line limit (ADR-0002) but skips hidden directories, and the generated file will exceed 500 lines (ADR-0012 clause 2). Add `src/api/.generated` to `ignores` in `frontend/eslint.config.js` (flat config does not ignore dot-directories on its own).
- Mark both generated files in `.gitattributes` (`linguist-generated=true`) so reviews collapse them.
- CI job `api-contract` in `.github/workflows/ci.yml`: set up Python 3.12 and Node 20 (same versions as the other jobs), `pip install -r requirements.txt`, `python scripts/export_openapi.py`, `cd frontend && npm ci && npm run generate:api`, then `git diff --exit-code -- frontend/openapi.json frontend/src/api/.generated/schema.d.ts`. The failure message should print the two commands contributors run to fix it.
- Add a short 'Regenerating API types' section to the root `CLAUDE.md` (replacing the manual verification checklist's first two bullets) and `frontend/CLAUDE.md`.
- Do not import the generated types anywhere yet; adopting them is TASK-0044. `tsc -b` must still compile the file (`skipLibCheck` is true, which also covers `.d.ts`).

## Notes and Risks
- Generated output must be deterministic: pin the generator version and keep `sort_keys` in the exporter, otherwise the drift check flaps.
- `spec-ops audit dependencies` scans Python manifests; confirm whether it also scans `package.json` and add a licence entry if it does (openapi-typescript is MIT).
- The job needs both toolchains and takes about 2 minutes; run it on every PR (no path filter) so it can become a required check.

## Dependencies
- TASK-0042 provides the exporter.
- TASK-0009 makes `tsc -b` a CI gate; generated types only protect anything once type checks run in CI.

## Definition of Done
- [ ] `npm run generate:api` in `frontend/` regenerates the file with no diff on a clean checkout.
- [ ] A pull request that renames a field in a response schema in `app/schemas/` without regenerating fails the `api-contract` job with a non-empty diff.
- [ ] `spec-ops health` passes (the generated file is not counted) and `npm run lint` passes (the generated directory is ignored).
- [ ] `cd frontend && npx tsc -b` passes with the generated file present.

```gherkin
Scenario: API contract drift fails the pull request
  Given a pull request that renames a field in a Pydantic response schema
  And frontend/src/api/.generated/schema.d.ts is not regenerated
  When the CI Quality Gate workflow runs
  Then the contract-drift check fails with a non-empty git diff
```

## INVEST Criteria
- **Independent**: Ordered after TASK-0042, TASK-0009 (see Dependencies); otherwise executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Contract drift between backend and frontend becomes a CI failure instead of a runtime error; ADR-0012, PRD-0006 outcome 10, US-0006.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Medium: one PR touching several files; keep it under about 500 lines of changed source (excluding generated files and migrations' SQL boilerplate).
- **Testable**: CI job result for an unregenerated schema change (ADR-0004); generated artifacts are public build outputs (ADR-0003).
