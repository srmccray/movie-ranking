---
id: REFACTOR-app-routers-import_amazon
title: Refactor and Decompose Legacy File import_amazon.py
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

# TASK-REFACTOR-app-routers-import_amazon: Refactor Legacy File import_amazon.py

## Summary
The grandfathered debt file `app/routers/import_amazon.py` contains 765 lines and violates the hard file length invariant governed by ADR-0002 (<500 lines).
This task plans the incremental extraction of cohesive submodules (import_amazon_movie.py, import_amazon_match.py) and establishes a public barrel export facade.

## Target Submodule Decomposition Path
Target decomposition destination: `app/routers/import_amazon/` with submodules:
- `import_amazon_movie.py`: add_import_movie, skip_import_movie, update_import_movie_match, to_naive_utc, parse_release_date, calculate_confidence, upload_amazon_prime_csv, get_import_session, cancel_import_session
- `import_amazon_match.py`: match_movies_with_tmdb

## AST Decomposition Blueprint
Decomposition Blueprint for /Users/stephen/Projects/movie-ranking/app/routers/import_amazon.py (765 lines):
  Submodule 'import_amazon_movie.py' (~444 lines):
    - [function] add_import_movie (lines 453-608)
    - [function] skip_import_movie (lines 622-663)
    - [function] update_import_movie_match (lines 676-731)
    - [function] to_naive_utc (lines 47-56)
    - [function] parse_release_date (lines 59-73)
    - [function] calculate_confidence (lines 76-112)
    - [function] upload_amazon_prime_csv (lines 321-390)
    - [function] get_import_session (lines 403-438)
    - [function] cancel_import_session (lines 744-765)
  Submodule 'import_amazon_match.py' (~193 lines):
    - [function] match_movies_with_tmdb (lines 115-307)
  Suggested barrel exports:
    from .import_amazon_movie import add_import_movie, skip_import_movie, update_import_movie_match, to_naive_utc, parse_release_date, calculate_confidence, upload_amazon_prime_csv, get_import_session, cancel_import_session
    from .import_amazon_match import match_movies_with_tmdb
    
    __all__ = ["add_import_movie", "skip_import_movie", "update_import_movie_match", "to_naive_utc", "parse_release_date", "calculate_confidence", "upload_amazon_prime_csv", "get_import_session", "cancel_import_session", "match_movies_with_tmdb"]

## INVEST Criteria
- **Independent**: Executed in isolated task branch without modifying shared backlog on branch.
- **Negotiable**: Concrete boundaries derived from AST seams.
- **Valuable**: Retires grandfathered technical debt from `.specops/grandfathered_debt.json`.
- **Estimable**: Symbol-level decomposition blueprint provided.
- **Small (<500 lines)**: Target submodules each strictly under 400 lines.
- **Testable**: Validated via blackbox frontdoor tests (ADR-0003).
