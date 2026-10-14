# SpecOps CLI Primer & Lifecycle Cheatsheet

This primer documents the public CLI entry points of SpecOps for orchestrators, agents, and human leads. SpecOps is managed via the `spec-ops <command>` CLI (installed as a standalone tool; CI pins it from GitHub).

---

## 1. Codebase Health & Quality Invariants

Inspect hard invariants, file lengths (<500 lines per ADR-0002), and backlog queue synchronization:

```bash
# Run full codebase health check
spec-ops health

# Check supply-chain security policies and allowed licenses
spec-ops health --security

# Scan dependencies for CVEs and license allowlist compliance
spec-ops audit dependencies

# Check constitution drift between specops.toml and AGENTS.md
spec-ops constitution check

# Re-synchronize AGENTS.md while preserving custom invariants
spec-ops constitution sync
```

---

## 2. Product Discovery & PRDs

PRDs live in `docs/project/product/` across lifecycle stages (`idea/`, `shaped/`, `accepted/`, `shipped/`):

```bash
# Audit PRD decomposition state and buffer readiness
spec-ops prd audit PRD-XXXX

# Lint PRDs against falsifiable criteria and checkable outcomes
spec-ops prd lint docs/project/product/accepted/PRD-XXXX.md
```

---

## 3. Backlog Management & Task Scaffolding

Tasks live in `docs/project/backlog/` across `proposed/`, `refined/`, and `complete/`:

```bash
# Scaffold a new PMaC task with Definition of Ready frontmatter
spec-ops task create \
  --title "My New Feature Slice" \
  --bc core \
  --prd PRD-0006 \
  --story US-0117 \
  --adr ADR-0001,ADR-0003 \
  --stage proposed \
  --non-interactive

# Show backlog flow and JIT buffer telemetry (add --once for a snapshot)
spec-ops backlog flow --once

# Detect circular dependency deadlocks and choke points
spec-ops backlog bottlenecks

# Diagnose and repair backlog health (orphans, cycle blocks, priority drift)
spec-ops backlog doctor --repair
```

---

## 4. Cognitive Backlog Curation (JIT Refinement)

Curate proposed tasks into the ready buffer (`refined/`) to maintain ~10 ready tasks:

```bash
# Dry-run cognitive curation to inspect proposed tasks and architectural drift
spec-ops curate --infer --dry-run

# Execute cognitive curation (promotes tasks, reconciles drift, synthesizes DoR criteria)
spec-ops curate --infer

# Traditional priority-based curation buffer fill
spec-ops curate
```

---

## 5. Worktree Sandboxing & Worker Execution

SpecOps enforces strict backlog isolation (ADR-0005) by executing in isolated git worktrees:

```bash
# Scaffold a human or agent worktree for a task
spec-ops worktree start TASK-XXXX

# Verify preflight, merge under MERGE_LOCK, and clean up the worktree
spec-ops worktree finish --task-id TASK-XXXX

# List active/stalled worktrees
spec-ops rescue --list

# Run autonomous worker on the next ready task
spec-ops worker

# Target a specific refined task
spec-ops worker --task TASK-XXXX --dry-run

# Run full autonomous cycle with concurrent worker batching
spec-ops cycle --max-workers 2
```

---

## 6. Worktree Rescue & Failure Triage

When a task fails or stalls during autonomous development:

```bash
# Inspect stalled worktree diagnostics and error logs
spec-ops rescue inspect TASK-XXXX

# Salvage partial progress and stage clean files into a human branch
spec-ops rescue salvage TASK-XXXX --files app/

# Reset stalled task with anti-loop failure memory to prevent recurring errors
spec-ops rescue reset TASK-XXXX --anti-loop

# Clean up orphaned worktree directories and branches safely
spec-ops rescue prune --older-than 7d
```

---

## 7. Quality Gates & Frontdoor Verification

Ensure 100% blackbox frontdoor pass rate before finalizing:

```bash
# Run backend test suite (the specops.toml preflight)
venv/bin/pytest

# Run frontend lint and tests (inside frontend/)
npm run lint && npm run test:run

# Audit for illegal private backdoor mocks (ADR-0003)
spec-ops test audit-anti-mock
```

---

## 8. Documentation, Visualizer & Release Management

```bash
# Build Diataxis documentation site
spec-ops docs build

# Launch zero-dependency living 2D graph visualizer
spec-ops visualizer --serve --port 8080

# Generate customer-facing release notes and business changelog
spec-ops release notes --milestone M1

# Export executive roadmaps and stakeholder presentations
spec-ops report burndown --format html
```
