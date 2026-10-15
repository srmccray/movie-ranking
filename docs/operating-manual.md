# movie-ranking Agent Operating Manual

Welcome to **movie-ranking**, managed via **SpecOps**—the opinionated, autonomous Project Management as Code (PMaC) engine for human architects and AI coding assistants.

All specifications, user stories, tasks, and architectural decisions are version-locked directly in git alongside implementation code.

---

## Hard Invariants

These rules are non-negotiable. Autonomous agents and human contributors must follow them without exception:

1. **File Length Limit (<500 lines)**:
   - Source files over ~500 lines are strictly forbidden. Decompose large files into focused, single-responsibility modules.
   - Enforced by `spec-ops health` (warns proactively at >=400 lines). Governed by ADR-0002.
2. **Blackbox Frontdoor Verification**:
   - Tests must exercise public interfaces (HTTP API endpoints, rendered UI behavior) rather than reaching into private internals or backdoor state manipulation.
   - Governed by ADR-0003.
3. **Strict Backlog Isolation**:
   - Multi-agent workers execute in isolated git worktrees (`.worktrees/<task-id>`) on dedicated task branches (`task/<task-id>` or `feat/<task-id>`).
   - Shared backlog files (`docs/project/backlog/`) must never be modified directly on feature branches; transitions are synchronized upon integration.
   - Governed by ADR-0005.
4. **Project Toolchain**:
   - Backend Python dependencies live in `requirements.txt` / `requirements-dev.txt` and run in the repo-root `venv/`. Backend tests: `venv/bin/pytest` (the `specops.toml` preflight). Frontend (`frontend/`) uses npm. SpecOps is the standalone `spec-ops` CLI (there is no UV workspace or `uv.lock`).
5. **Specification as Code (PMaC)**:
   - Every requirement, persona, architectural decision, and work item lives under `docs/project/` as Markdown with YAML frontmatter.
   - Governed by ADR-0001.
6. **Executable BDD User Stories & Frontdoor Testing**:
   - User stories in `docs/project/user_stories/accepted/` must provide executable Gherkin scenarios.
   - All acceptance tests must verify observable outcomes without private mock backdoors.
   - Governed by ADR-0006.

<!-- BEGIN CUSTOM INVARIANTS -->
7. **Project Layout & Verification Commands**:
   - Components (`specops.toml`): `backend` = `app/` (FastAPI), `frontend` = `frontend/src` (React/TypeScript), `infra` = `infra/lib` (AWS CDK). Backend tests live in `tests/`.
   - Backend: `venv/bin/pytest`. Frontend (run inside `frontend/`): `npm run lint`, `npm run test:run`, `npm run build`.
   - Installed profiles are `core` and `bdd` (ADR-0001 to ADR-0006). The DDD, property-testing, and mutation-testing profiles are not installed, so Hypothesis and Mutmut are not required.
   - Pre-existing files over the limit are grandfathered in `specops.toml` (`[invariants.file_limits]`) and `.specops/grandfathered_debt.json`, and tracked by `TASK-REFACTOR-*` tasks in `docs/project/backlog/`.
<!-- END CUSTOM INVARIANTS -->

---

## Design Principles

- **Version-Locked Specifications**: Requirements, user stories, and tasks live in the exact same git commit history as implementation code.
- **Thin Vertical Slicing**: Decompose PRDs into thin, single-pass vertical slices and architectural spikes rather than speculative horizontal layers.
- **Just-In-Time (JIT) Refinement**: Maintain a lean buffer of ~10 ready tasks in `refined/` to prevent specification rot before work begins.
- **Living Relational Graph**: Maintain bidirectional traceability from Personas -> PRDs -> Stories -> Tasks -> ADRs -> Commits.

---

## Project Structure & Navigation

All project management specifications live under `docs/project/`:

| Directory | Purpose |
|---|---|
| `docs/project/user_stories/PERSONAS.md` | Core user personas defining user needs and pain points |
| `docs/project/product/` | PRDs progressing from `idea/` to `shaped/`, `accepted/`, and `shipped/` |
| `docs/project/user_stories/` | Gherkin user stories defining end-to-end user journeys |
| `docs/project/adrs/` | Architectural Decision Records organized with `REGISTRY.md` |
| `docs/project/backlog/` | Work items in `complete/`, `refined/`, and `proposed/` |
| `docs/project/backlog/PRIORITY.md` | Strict sequential priority queue for engineering tasks |
| `docs/project/backlog/ROADMAP.md` | High-level delivery milestones |

---

## Documentation Directives (Diataxis Standards)

All system documentation outside `docs/project/` follows the **Diataxis framework** (`tutorials/`, `how-to/`, `reference/`, `explanation/`):

1. **Consult Existing Docs**: Search `docs/` before implementing changes or adding new conventions.
2. **Fix Stale Documentation**: Update inaccurate or outdated documentation discovered during your work.
3. **Document Reusable Capabilities**: When introducing or modifying public CLI flags, APIs, or architectural patterns, author corresponding how-to recipes or reference specs in `docs/`.

---

## Definition of Ready (DoR)

A backlog task or feature may only be transitioned to `refined/` and pulled into active development when:

1. **Task Metadata Complete**: Task frontmatter contains `id`, `title`, `status: Refined`, `target_bc`, and explicit dependencies.
2. **Governing Artifacts Linked**: Reference PRD in `docs/project/product/accepted/`, Persona in `docs/project/user_stories/PERSONAS.md`, and governing ADRs in `docs/project/adrs/accepted/` are cited.
3. **Executable BDD Specification**: Governing user story in `docs/project/user_stories/accepted/` provides executable Gherkin scenarios (`Given ... When ... Then`) whose test setup is achievable strictly through public frontdoors without backdoor tampering (ADR-0006).
4. **INVEST Criteria Satisfied**: Validated as a thin vertical slice (Independent, Negotiable, Valuable, Estimable, Small [<500 lines per file], Testable) with zero speculative horizontal layers.
5. **Documentation Review**: Relevant existing documentation in `docs/` reviewed to prevent conflicting conventions.

---

## Definition of Done (DoD)

Work is complete and ready for integration into `main` only when:

1. **Blackbox Frontdoor Verification**: 100% test pass rate (`venv/bin/pytest` for the backend; `npm run test:run` in `frontend/` for the frontend) verifying observable contracts through public frontdoors with zero private mock backdoors (ADR-0003).
2. **Executable BDD Scenarios Passing**: All Gherkin acceptance criteria pass cleanly without mock backdoors; UI scenarios are automated with Playwright (ADR-0006).
3. **Codebase Health Check**: `spec-ops health` reports 0 file limit violations (<500 lines) and 0 proactive warnings (<400 lines), and verifies `PRIORITY.md` sync (ADR-0002).
4. **Documentation Integrity (Diataxis)**:
   - Inaccurate or stale docs discovered during work are corrected.
   - Reusable patterns, CLI commands, and architectural changes documented in `docs/how-to/` or `docs/reference/`.
   - Documentation builds cleanly (`spec-ops docs build`).
5. **Strict Backlog Progression**: Task is moved from `refined/` to `complete/` (or via `spec-ops queue complete <task-id>`) and `PRIORITY.md` updated atomically upon integration (ADR-0005).
6. **Commit Provenance**: Commits include structured trailers referencing governing tasks and stories (`SpecOps-Task: TASK-XXXX`).

---

## Task Execution Workflow

When picking up engineering work:

1. **Select Task**: Always select the highest-priority unassigned task in `docs/project/backlog/PRIORITY.md` located in `refined/`.
2. **Review Invariants & DoR**: Verify task meets the Definition of Ready (DoR); read governing ADRs, PRDs, and user stories cited in the frontmatter.
3. **Implement**: Develop the solution using test-driven development through public frontdoors. Maintain BDD scenarios alongside feature code.
4. **Preflight Verification**:
   - Run `spec-ops health` (verify 0 file limit violations, 0 warnings, and PRIORITY.md sync).
   - Run `venv/bin/pytest` (verify 100% backend test pass rate), and for frontend changes `npm run lint` and `npm run test:run` inside `frontend/`.
5. **Complete**: Verify all Definition of Done (DoD) criteria; move task to `complete/` or use `spec-ops queue complete <task-id>`, update `PRIORITY.md`, and link commit or PR.
