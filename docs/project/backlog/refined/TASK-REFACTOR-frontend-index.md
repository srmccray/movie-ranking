---
id: REFACTOR-frontend-index
title: Refactor and Decompose Legacy File index.css
status: Refined
governing_adrs:
- ADR-0002
governing_prds:
- PRD-0005
governing_stories:
- US-0005
target_bc: core
---

# TASK-REFACTOR-frontend-index: Refactor Legacy File index.css

## Summary
The grandfathered debt file `frontend/src/index.css` contains 3355 lines and violates the hard file length invariant governed by ADR-0002 (<500 lines).
This task plans the incremental extraction of cohesive submodules (index_part1.py, index_part2.py) and establishes a public barrel export facade.

## Target Submodule Decomposition Path
Target decomposition destination: `frontend/src/index/` with submodules:
- `index_part1.py`: 
- `index_part2.py`: 

## AST Decomposition Blueprint
Decomposition Blueprint for /Users/stephen/Projects/movie-ranking/frontend/src/index.css (3355 lines):
  Submodule 'index_part1.py' (~0 lines):
  Submodule 'index_part2.py' (~0 lines):

## INVEST Criteria
- **Independent**: Executed in isolated task branch without modifying shared backlog on branch.
- **Negotiable**: Concrete boundaries derived from AST seams.
- **Valuable**: Retires grandfathered technical debt from `.specops/grandfathered_debt.json`.
- **Estimable**: Symbol-level decomposition blueprint provided.
- **Small (<500 lines)**: Target submodules each strictly under 400 lines.
- **Testable**: Validated via blackbox frontdoor tests (ADR-0003).
