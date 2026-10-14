---
id: REFACTOR-tests-test_movies
title: Refactor and Decompose Legacy File test_movies.py
status: Proposed
created: 2026-09-29
governing_adrs:
  - ADR-0002
target_bc: core
---

# TASK-REFACTOR-tests-test_movies: Refactor Legacy File test_movies.py

## Summary
The grandfathered debt file `tests/test_movies.py` contains 608 lines and violates the hard file length invariant governed by ADR-0002 (<500 lines).
This task plans the incremental extraction of cohesive submodules (test_movies_create.py, test_movies_search.py) and establishes a public barrel export facade.

## Target Submodule Decomposition Path
Target decomposition destination: `tests/test_movies/` with submodules:
- `test_movies_create.py`: TestCreateMovie, TestMovieSearchAndCreate
- `test_movies_search.py`: TestSearchMovies

## AST Decomposition Blueprint
Decomposition Blueprint for /Users/stephen/Projects/movie-ranking/tests/test_movies.py (608 lines):
  Submodule 'test_movies_create.py' (~321 lines):
    - [class] TestCreateMovie (lines 23-201)
    - [class] TestMovieSearchAndCreate (lines 467-608)
  Submodule 'test_movies_search.py' (~261 lines):
    - [class] TestSearchMovies (lines 204-464)
  Suggested barrel exports:
    from .test_movies_create import TestCreateMovie, TestMovieSearchAndCreate
    from .test_movies_search import TestSearchMovies
    
    __all__ = ["TestCreateMovie", "TestMovieSearchAndCreate", "TestSearchMovies"]

## INVEST Criteria
- **Independent**: Executed in isolated task branch without modifying shared backlog on branch.
- **Negotiable**: Concrete boundaries derived from AST seams.
- **Valuable**: Retires grandfathered technical debt from `.specops/grandfathered_debt.json`.
- **Estimable**: Symbol-level decomposition blueprint provided.
- **Small (<500 lines)**: Target submodules each strictly under 400 lines.
- **Testable**: Validated via blackbox frontdoor tests (ADR-0003).
