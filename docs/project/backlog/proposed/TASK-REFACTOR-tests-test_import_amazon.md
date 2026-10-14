---
id: REFACTOR-tests-test_import_amazon
title: Refactor and Decompose Legacy File test_import_amazon.py
status: Proposed
created: 2026-09-29
governing_adrs:
  - ADR-0002
governing_prds:
  - PRD-0005
governing_stories:
  - US-0005
target_bc: core
---

# TASK-REFACTOR-tests-test_import_amazon: Refactor Legacy File test_import_amazon.py

## Summary
The grandfathered debt file `tests/test_import_amazon.py` contains 1409 lines and violates the hard file length invariant governed by ADR-0002 (<500 lines).
This task plans the incremental extraction of cohesive submodules (test_import_amazon_movie.py, test_import_amazon_csv.py) and establishes a public barrel export facade.

## Target Submodule Decomposition Path
Target decomposition destination: `tests/test_import_amazon/` with submodules:
- `test_import_amazon_movie.py`: TestAddMovie, TestSkipMovie, TestUpdateMovieMatch, create_mock_tmdb_result, TestGetSession, TestCancelSession, TestFullImportFlow
- `test_import_amazon_csv.py`: create_test_csv, TestUploadCSV

## AST Decomposition Blueprint
Decomposition Blueprint for /Users/stephen/Projects/movie-ranking/tests/test_import_amazon.py (1409 lines):
  Submodule 'test_import_amazon_movie.py' (~1202 lines):
    - [class] TestAddMovie (lines 340-622)
    - [class] TestSkipMovie (lines 625-753)
    - [class] TestUpdateMovieMatch (lines 756-1081)
    - [function] create_mock_tmdb_result (lines 36-65)
    - [class] TestGetSession (lines 228-337)
    - [class] TestCancelSession (lines 1084-1190)
    - [class] TestFullImportFlow (lines 1193-1409)
  Submodule 'test_import_amazon_csv.py' (~171 lines):
    - [function] create_test_csv (lines 21-33)
    - [class] TestUploadCSV (lines 68-225)
  Suggested barrel exports:
    from .test_import_amazon_movie import TestAddMovie, TestSkipMovie, TestUpdateMovieMatch, create_mock_tmdb_result, TestGetSession, TestCancelSession, TestFullImportFlow
    from .test_import_amazon_csv import create_test_csv, TestUploadCSV
    
    __all__ = ["TestAddMovie", "TestSkipMovie", "TestUpdateMovieMatch", "create_mock_tmdb_result", "TestGetSession", "TestCancelSession", "TestFullImportFlow", "create_test_csv", "TestUploadCSV"]

## INVEST Criteria
- **Independent**: Executed in isolated task branch without modifying shared backlog on branch.
- **Negotiable**: Concrete boundaries derived from AST seams.
- **Valuable**: Retires grandfathered technical debt from `.specops/grandfathered_debt.json`.
- **Estimable**: Symbol-level decomposition blueprint provided.
- **Small (<500 lines)**: Target submodules each strictly under 400 lines.
- **Testable**: Validated via blackbox frontdoor tests (ADR-0003).
