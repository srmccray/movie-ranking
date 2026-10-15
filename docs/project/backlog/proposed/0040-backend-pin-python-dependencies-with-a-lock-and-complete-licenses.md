---
id: '0040'
title: 'requirements.txt: pin Python dependencies from a single source and complete docs/project/compliance/licenses.json'
status: Proposed
governing_adrs:
- ADR-0009
- ADR-0001
governing_prds:
- PRD-0007
governing_stories:
- US-0009
dependencies: []
target_bc: backend
priority: P2
---

# TASK-0040: requirements.txt: pin Python dependencies from a single source and complete docs/project/compliance/licenses.json

## Summary
`requirements.txt` uses open ranges (`fastapi>=0.109.0`, `sqlalchemy[asyncio]>=2.0.0`, ...) and three entries with no constraint at all (`asyncpg`, `pydantic-settings`, `python-multipart`), with no lock file. Every CI run and every Lambda build resolves whatever is newest, so builds are not reproducible and a bad upstream release ships to production. Pin everything from one source and keep the licence manifest complete.

Priority: P2. Size: M. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- Inputs today: `requirements.txt` (14 direct packages: fastapi, uvicorn[standard], sqlalchemy[asyncio], asyncpg, alembic, python-jose[cryptography], bcrypt, google-auth, requests, pydantic[email], pydantic-settings, python-multipart, httpx, mangum) and `pyproject.toml` `dependencies` (10 packages; it lacks google-auth, requests, httpx and mangum, so it is already stale). Consumers: `.github/workflows/ci.yml` (`pip install -r requirements.txt` plus ad hoc `pytest pytest-asyncio httpx aiosqlite`), `.github/workflows/deploy.yml` (`pip install -r /var/task/requirements.txt -t /opt/package` in the arm64 Docker build), the `Dockerfile` (`COPY requirements.txt`).
- Make `pyproject.toml` the single hand-edited source: complete its `dependencies` list to the 14 packages and put test tools (`pytest`, `pytest-asyncio`, `httpx`, `aiosqlite`, `boto3` from TASK-0029) in the `dev` extra. Generate pinned files with uv (already installed in the CI preflight job): `uv pip compile pyproject.toml --python-version 3.12 --universal -o requirements.txt` and `uv pip compile pyproject.toml --extra dev --python-version 3.12 --universal -o requirements-dev.txt`. `--universal` keeps the output valid for the arm64 Lambda build and x86 CI. Add a header comment with the regeneration command.
- Switch the workflows to install `requirements.txt` (+ `requirements-dev.txt` for tests) so CI and Lambda use the same pins; verify the Docker arm64 build still resolves wheels for `asyncpg`, `bcrypt` and `cryptography`.
- Licences: `docs/project/compliance/licenses.json` lists 8 packages (fastapi, uvicorn, asyncpg, alembic, python-jose, bcrypt, pydantic-settings, python-multipart). Add entries for the six missing direct dependencies: sqlalchemy (MIT), google-auth (Apache-2.0), requests (Apache-2.0), pydantic (MIT), httpx (BSD-3-Clause), mangum (MIT), plus any other direct package added by this task; copy the `source` wording of existing entries. Verify each licence against the installed metadata (`pip show`/`importlib.metadata`) rather than from memory.
- Document the workflow in the root `CLAUDE.md` 'How We Work' step 2 (it already says to add a `licenses.json` entry whenever a dependency is added to `requirements.txt`): now 'edit `pyproject.toml`, run the compile command, add the licence entry'.

## Notes and Risks
- Upgrade policy: Dependabot (TASK-0041) proposes bumps as PRs; the compile command is re-run in those PRs by a CI check that fails if `requirements.txt` is not what `uv pip compile` would produce.
- `python-jose` is poorly maintained; replacing it with PyJWT is a separate decision and stays out of scope here.
- Pinning exposes transitive packages that need licence review; if `spec-ops audit dependencies` (run it locally) starts flagging them, add entries rather than loosening the check.

## Definition of Done
- [ ] `requirements.txt` contains only `==` pins (no `>=`, no unversioned lines) and is reproducible: re-running the documented `uv pip compile` command produces no diff.
- [ ] CI and the Lambda build install from the pinned files; the CI run is green and a deploy build completes (verify with a `workflow_dispatch` build step without publishing, or inspect the job log).
- [ ] `docs/project/compliance/licenses.json` has an entry for every package in `pyproject.toml` `dependencies`, and `spec-ops audit dependencies` exits 0.
- [ ] A CI step fails when `requirements.txt` is out of date relative to `pyproject.toml`.

```gherkin
Scenario: Builds install exactly the pinned versions
  Given requirements.txt contains only pinned versions
  When CI and the Lambda build install dependencies on different days
  Then both install the same package versions
```

## INVEST Criteria
- **Independent**: No task dependencies; executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Reproducible builds and a licence manifest that matches reality; PRD-0007 outcome 10, US-0009.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Medium: one PR touching several files; keep it under about 500 lines of changed source (excluding generated files and migrations' SQL boilerplate).
- **Testable**: Compile-and-diff check in CI and the package list visible in job logs (ADR-0001 spec-as-code).
