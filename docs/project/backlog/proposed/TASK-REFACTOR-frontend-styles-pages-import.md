---
id: REFACTOR-frontend-styles-pages-import
title: Refactor and Decompose Legacy File import.css
status: Proposed
created: 2026-09-29
governing_adrs:
  - ADR-0002
target_bc: core
---

# TASK-REFACTOR-frontend-styles-pages-import: Refactor Legacy File import.css

## Summary
The grandfathered debt file `frontend/src/styles/pages/import.css` contains 619 lines and violates the hard file length invariant governed by ADR-0002 (<500 lines).
This task plans the incremental extraction of cohesive submodules (import_part1.py, import_part2.py) and establishes a public barrel export facade.

## Target Submodule Decomposition Path
Target decomposition destination: `frontend/src/styles/pages/import/` with submodules:
- `import_part1.py`: 
- `import_part2.py`: 

## AST Decomposition Blueprint
Decomposition Blueprint for /Users/stephen/Projects/movie-ranking/frontend/src/styles/pages/import.css (619 lines):
  Submodule 'import_part1.py' (~0 lines):
  Submodule 'import_part2.py' (~0 lines):

## INVEST Criteria
- **Independent**: Executed in isolated task branch without modifying shared backlog on branch.
- **Negotiable**: Concrete boundaries derived from AST seams.
- **Valuable**: Retires grandfathered technical debt from `.specops/grandfathered_debt.json`.
- **Estimable**: Symbol-level decomposition blueprint provided.
- **Small (<500 lines)**: Target submodules each strictly under 400 lines.
- **Testable**: Validated via blackbox frontdoor tests (ADR-0003).
