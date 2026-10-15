# Movie Ranking Project

This document defines project-wide conventions that apply across the entire codebase. For domain-specific guidance, see the detailed guides in each directory.

## Detailed Guides

| Guide | Purpose |
|-------|---------|
| [`frontend/CLAUDE.md`](frontend/CLAUDE.md) | React/TypeScript development, components, hooks, styling |
| [`app/CLAUDE.md`](app/CLAUDE.md) | FastAPI backend, models, schemas, routers, migrations |
| [`infra/CLAUDE.md`](infra/CLAUDE.md) | AWS CDK infrastructure, CloudFront, Lambda, deployment |

## Critical Conventions

### Trailing Slashes (MUST FOLLOW)

**All API endpoints use trailing slashes.** This is critical for FastAPI's redirect behavior and CORS compatibility.

```python
# Backend - Correct
@router.post("/")
@router.delete("/{ranking_id}/")

# Backend - Wrong (causes 404/redirect errors)
@router.delete("/{ranking_id}")
```

Current exceptions: `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, and `GET /health` have no trailing slash. Do not copy them for new endpoints.

```typescript
// Frontend - Correct
await fetch(`/api/v1/rankings/${id}/`, { method: 'DELETE' });

// Frontend - Wrong
await fetch(`/api/v1/rankings/${id}`, { method: 'DELETE' });
```

### DateTime Handling

**Strategy: Naive UTC.** The database uses `TIMESTAMP WITHOUT TIME ZONE`. All datetimes are stored as naive UTC.

| Layer | Format |
|-------|--------|
| Frontend sends | ISO 8601 with timezone: `new Date().toISOString()` |
| Backend converts | Naive UTC before storage |
| Database stores | `TIMESTAMP WITHOUT TIME ZONE` |

```python
# Backend conversion: app/utils/time.py (single shared module, ADR-0010)
from app.utils.time import to_naive_utc, utc_now_naive

rated_at = to_naive_utc(payload.rated_at) or utc_now_naive()
```

### HTTP Status Codes

| Code | Usage |
|------|-------|
| `200` | Successful update/read |
| `201` | Successful creation (`POST /movies/` returns 200 instead when the TMDB id already exists) |
| `204` | Successful deletion (no content) |
| `401` | Not authenticated |
| `403` | Not authorized (wrong user) |
| `404` | Resource not found |
| `422` | Validation error |

## API Contract Verification

**Critical:** Frontend and backend types must match exactly. Runtime errors occur when they don't.

### Common Pitfall

```typescript
// Backend returns: { results: [...], query: "...", year: null }

// WRONG - Frontend assumes raw array
async searchMovies(): Promise<SearchResult[]> {
  return this.request<SearchResult[]>('/search/');  // Runtime error!
}

// CORRECT - Frontend matches backend wrapper
async searchMovies(): Promise<SearchResult[]> {
  const response = await this.request<SearchResponse>('/search/');
  return response.results;
}
```

### Verification Checklist

- [ ] Wrapper responses (`*ListResponse`, `*SearchResponse`) contain data in a field like `items` or `results`
- [ ] Field names use `snake_case` (matching Python/JSON convention)

### Regenerating API types

`frontend/openapi.json` and `frontend/src/api/.generated/schema.d.ts` are generated from the backend and committed. After changing anything under `app/schemas/` or a router's `response_model`, regenerate both; the `api-contract` CI job fails on any diff:

```bash
venv/bin/python scripts/export_openapi.py
cd frontend && npm run generate:api
```

Export the OpenAPI schema offline (no server or database needed; ADR-0012):

```bash
venv/bin/python scripts/export_openapi.py            # writes frontend/openapi.json
venv/bin/python scripts/export_openapi.py --out /tmp/openapi.json
```

`tests/test_api_conventions.py` enforces trailing slashes and declared responses on every `/api/v1` route.

For detailed patterns, see:
- `frontend/CLAUDE.md` - "API Contract Verification" section
- `app/CLAUDE.md` - "Frontend API Contract Documentation" section

## Documentation Structure

All project documentation is stored in `docs/project/` (SpecOps layout; validate with `spec-ops health`; also `prd audit`, `trace`):

```
docs/project/                          # SpecOps project-management-as-code tree
├── product/                           # PRDs (create with `spec-ops prd create`)
│   ├── idea/ shaped/ accepted/        #   lifecycle stages (SMALL sketches start in idea/)
│   ├── shipped/                       #   delivered features
│   └── REGISTRY.md
│       # prd-NNNN-{feature-slug}.md: YAML frontmatter + Who/Cannot-do-today/
│       # What-good-looks-like/Non-goals/Checkable Outcomes; refinement notes
│       # go in a `## Refinement Notes` section of the same PRD
├── backlog/                           # Tasks (TASK-NNNN), frontmatter `governing_prds`
│   ├── proposed/ refined/ complete/   #   NNNN-{feature-slug}-{name}.md
│   ├── PRIORITY.md                    #   execution order (replaces tasks/_index.md)
│   └── ROADMAP.md
├── user_stories/                      # Personas + Gherkin user stories (US-NNNN)
│   ├── PERSONAS.md  REGISTRY.md
│   └── accepted/us-NNNN-{slug}.md
├── adrs/                              # Architecture Decision Records
│   ├── accepted/adr-NNNN-{slug}.md
│   └── REGISTRY.md
└── archive/                           # Completed/legacy documentation
    ├── plans/                         # Old .claude/plans/ content
    └── docs/                          # Old docs/ content
```

## Agent Workflow

Specialized agents handle different aspects of development. See `.claude/agents/` for agent definitions. The tiers and agents below govern how a feature is planned and shaped; [How We Work](#how-we-work) governs how a backlog task is executed.

### Feature Development Tiers

| Tier | Process |
|------|---------|
| TRIVIAL | Direct implementation |
| SMALL | Quick Sketch -> Implementation |
| MEDIUM | FRD -> Light Refinement -> Implementation |
| LARGE | FRD -> Thorough Refinement -> Task Breakdown -> Implementation |

### Key Agents

| Agent | Purpose |
|-------|---------|
| `request-triage` | Categorizes requests and determines workflow |
| `frd-creator` | Creates Feature Requirements Documents |
| `frd-refiner` | Refines FRDs against codebase patterns |
| `frd-task-breakdown` | Breaks features into implementable tasks |
| `backend-implementation` | Implements backend features |
| `frontend-implementation` | Implements frontend features |
| `test-coverage` | Adds/improves test coverage |
| `documentation-writer` | Creates/updates documentation |
| `infrastructure-implementation` | Implements AWS CDK infrastructure |
| `security-review` | Reviews auth flows and security-sensitive code |
| `workflow-orchestrator` | Entry point; recommends which agent to invoke next |

## How We Work

SpecOps is the planning and guardrail layer; Claude Code is the execution layer. SpecOps is installed pinned (CI pins commit `9745c40` of `tyevans/spec-ops`); the local CLI is `spec-ops` on PATH.

1. **Plan.** `spec-ops prd create` -> `spec-ops story create` -> write tasks into `docs/project/backlog/proposed/`. Review and edit everything generated: `spec-ops prd decompose` produces generic boilerplate.
2. **Pick work.** `spec-ops queue next` shows the next ready task from `docs/project/backlog/refined/`. `spec-ops curate` refills the refined buffer (target 10). Curation's dependency-audit gate reads `docs/project/compliance/licenses.json`: add an entry there whenever a dependency is added, otherwise curate silently promotes nothing. Dependencies are pinned: edit `pyproject.toml` (the only hand-edited source), regenerate with `uv pip compile pyproject.toml --python-version 3.12 --universal -o requirements.txt` and `uv pip compile pyproject.toml --extra dev --python-version 3.12 --universal -o requirements-dev.txt`, then add the licence entry. CI fails if the pinned files are stale.
3. **Execute.** One task per feature branch `feat/task-<id>`, in a git worktree under `.worktrees/` (gitignored):

   ```bash
   git worktree add .worktrees/task-<id> -b feat/task-<id> main
   ```

   The worktree has no `venv/` or `node_modules/`. Run backend tests with the absolute path to the primary checkout's `venv/bin/pytest` (for frontend tasks, symlink or install the deps). Follow the task file's blueprint, its Definition of Done, and the governing ADRs. Before opening the PR:
   - Backend: `venv/bin/pytest`
   - Frontend (only if frontend code changed): `npm run test:run` in `frontend/`
   - `spec-ops health` exits 0
   - `spec-ops trace` if docs or specs changed

   Do not use `git commit --no-verify` to get past the pre-commit hook without the maintainer's approval. Known false positives: the secret scanner can flag npm integrity hashes in `frontend/package-lock.json`, and it re-scans whole files, so moving a test file can resurface an old fixture credential. For a test fixture, add the scanner's inline opt-out `# pragma: allowlist secret` to that one line (never change scanner config); if more than a line or two are flagged, stop and ask.
   Two identical copies of the debt baseline exist: `.specops/grandfathered_debt.json` and `.spec-ops/debt_baseline.json`. Update both (and `specops.toml`'s `grandfathered` list) when a task retires a grandfathered file.
4. **PR.** Push the branch and open a PR to `main`. CI (`.github/workflows/ci.yml`: numbering, health, backend tests) must pass before merge. Feature branches must NOT touch `docs/project/backlog/` (ADR-0005).
5. **Complete.** After the PR merges, with the task's branch deleted and from `main` (never from a feature branch), run the completion gate, then commit the result on a short-lived branch as its own small PR. `spec-ops queue complete <task-id>` does this for numeric IDs (`TASK-0008`): it moves the task file to `docs/project/backlog/complete/` and syncs `PRIORITY.md`. It rejects `TASK-REFACTOR-*` IDs as "not found" (it uppercases the ID before matching), so for those call the same gate through spec-ops' Python API:

   ```
   $(head -1 ~/.local/bin/spec-ops | sed 's/^#!//') - <<'EOF'
   from pathlib import Path
   from spec_ops.config.loader import load_config
   from spec_ops.backlog.queue import BacklogQueue
   from spec_ops.app.task_lifecycle import TaskLifecycleService
   cfg = load_config(root_dir=Path.cwd())
   t = next(t for t in BacklogQueue(cfg.backlog_dir).list_all_tasks() if t.canonical_id == "TASK-REFACTOR-<name>")
   print(TaskLifecycleService(cfg).complete_task_with_gate(t, base_branch="main", repo_root=cfg.root_dir, config=cfg))
   EOF
   ```

   Run it on `main` with the task's branch already deleted: if the gate finds a live branch it squash-merges that branch into `main` and commits directly, and if the task has no recorded branch it falls back to the *current* branch. Then run `spec-ops health` and `spec-ops trace`, and `spec-ops curate` if the refined buffer dropped.

### SpecOps Commands to Avoid

| Command | Why |
|---------|-----|
| `spec-ops cycle` | Modifies `docs/project/` even with `--dry-run`: decomposes PRDs and creates junk tasks and stories |
| `spec-ops worker` (plain or `--drain`) | Its merge step squash-merges into local `main` with no push or PR, and its preflight uses relative paths that fail in worktrees |
| `spec-ops scaffold agents` | Overwrites the project-specific fixes in `AGENTS.md` |

Read-only: `spec-ops queue next`, `worker --dry-run` (creates and removes a temporary worktree), `health`, `trace`, `prd lint`, `story trace`, `curate --dry-run`. `spec-ops curate` without `--dry-run` writes to disk: it promotes tasks from `proposed/` to `refined/`.

## Git Conventions

- Do NOT include "Co-Authored-By: Claude" or any Claude attribution in commit messages
- Keep commit messages concise and descriptive
- Use present tense ("Add feature" not "Added feature")

## Before Implementing New Features

### Checklist

- [ ] Examine 3+ similar implementations in the codebase
- [ ] Review the relevant detailed guide (`frontend/CLAUDE.md` or `app/CLAUDE.md`)
- [ ] Verify trailing slash convention matches existing endpoints
- [ ] Match datetime handling patterns (naive UTC conversion)
- [ ] Plan API contracts before implementing (check both frontend types and backend schemas)
- [ ] Write integration tests with realistic frontend requests
