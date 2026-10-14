# User Personas

Archetypes representing the end users, maintainers, and automation interacting with Movie Ranking (a FastAPI backend in `app/`, a React frontend in `frontend/`, and AWS CDK infrastructure in `infra/`).

Casey is the only end-user persona and the target of PRD-0001 to PRD-0004. Alex is the target of PRD-0005. The other personas describe how the project's SpecOps workflow is used and are not yet referenced by a PRD or story.

---

## 1. Alex — The Systems Builder
- **Role**: Maintainer and architect of Movie Ranking who builds it together with AI coding agents.
- **Pain Points**:
  - Oversized legacy files (13 are grandfathered over the 500-line limit, e.g. `tests/test_import_amazon.py` and `frontend/src/index.css`) that agents cannot read or edit reliably.
  - Specifications drifting from the code (for example the legacy `.claude_docs/` plans that were migrated into `docs/project/`).
- **Goals with this platform**:
  - Keep every source file under 500 lines (ADR-0002) and drive grandfathered debt to zero (PRD-0005).
  - Unbroken traceability from user story to PRD to backlog task to commit.

---

## 2. Jordan — The Product Strategist
- **Role**: Product owner deciding what Movie Ranking builds next.
- **Pain Points**:
  - Unclear delivery status and vague completion criteria for features such as imports and analytics.
- **Goals with this platform**:
  - Use `docs/project/product/`, `backlog/PRIORITY.md`, and `backlog/ROADMAP.md` to see what has shipped and what is queued.
  - Write PRDs with checkable outcomes so "done" is observable.

---

## 3. Morgan — The Autonomous Agent
- **Role**: LLM-powered coding worker (for example the `backend-implementation` and `frontend-implementation` agents in `.claude/agents/`) that picks up refined backlog tasks such as the `TASK-REFACTOR-*` decompositions.
- **Pain Points**:
  - Ambiguous ticket descriptions with no clear definition of done.
  - Large files that exceed its working context.
- **Goals with this platform**:
  - Unambiguous task contracts that cite governing ADRs, PRDs, and stories, executed in an isolated git worktree.

---

## 4. Riley — The Human Developer
- **Role**: Developer who reviews and merges agent-authored changes to Movie Ranking, or pairs with an agent on a task.
- **Pain Points**:
  - Review fatigue on large diffs and opaque autonomous changes.
- **Goals with this platform**:
  - Small, single-purpose pull requests that keep `venv/bin/pytest`, the frontend tests, and `spec-ops health` green, with clear provenance back to the originating task.

---

## 5. Casey — The Movie Enthusiast
- **Role**: End user of Movie Ranking who rates and ranks films they have watched.
- **Pain Points**:
  - Tedious manual entry of previously watched movies (e.g. from Amazon Prime history).
  - Confusing errors when a login session expires.
  - A sparse ranked-movie list where cards are hard to scan.
- **Goals with this platform**:
  - Quickly build an accurate, good-looking ranked list of watched movies.
