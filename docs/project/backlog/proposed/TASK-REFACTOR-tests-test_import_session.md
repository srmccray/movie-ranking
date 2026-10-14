---
id: REFACTOR-tests-test_import_session
title: Refactor and Decompose Legacy File test_import_session.py
status: Proposed
created: 2026-09-29
governing_adrs:
  - ADR-0002
target_bc: core
---

# TASK-REFACTOR-tests-test_import_session: Refactor Legacy File test_import_session.py

## Summary
The grandfathered debt file `tests/test_import_session.py` contains 625 lines and violates the hard file length invariant governed by ADR-0002 (<500 lines).
This task plans the incremental extraction of cohesive submodules (test_import_session_store.py, test_import_session_core.py) and establishes a public barrel export facade.

## Target Submodule Decomposition Path
Target decomposition destination: `tests/test_import_session/` with submodules:
- `test_import_session_store.py`: TestImportSessionStoreCreate, TestImportSessionStoreGet, TestImportSessionStoreUpdate, TestImportSessionStoreDelete, TestImportSessionStoreCleanup, TestImportSessionStoreSessionCount, TestGlobalSessionStore
- `test_import_session_core.py`: TestImportSession

## AST Decomposition Blueprint
Decomposition Blueprint for /Users/stephen/Projects/movie-ranking/tests/test_import_session.py (625 lines):
  Submodule 'test_import_session_store.py' (~540 lines):
    - [class] TestImportSessionStoreCreate (lines 74-224)
    - [class] TestImportSessionStoreGet (lines 227-342)
    - [class] TestImportSessionStoreUpdate (lines 345-455)
    - [class] TestImportSessionStoreDelete (lines 458-503)
    - [class] TestImportSessionStoreCleanup (lines 506-586)
    - [class] TestImportSessionStoreSessionCount (lines 589-611)
    - [class] TestGlobalSessionStore (lines 614-625)
  Submodule 'test_import_session_core.py' (~49 lines):
    - [class] TestImportSession (lines 23-71)
  Suggested barrel exports:
    from .test_import_session_store import TestImportSessionStoreCreate, TestImportSessionStoreGet, TestImportSessionStoreUpdate, TestImportSessionStoreDelete, TestImportSessionStoreCleanup, TestImportSessionStoreSessionCount, TestGlobalSessionStore
    from .test_import_session_core import TestImportSession
    
    __all__ = ["TestImportSessionStoreCreate", "TestImportSessionStoreGet", "TestImportSessionStoreUpdate", "TestImportSessionStoreDelete", "TestImportSessionStoreCleanup", "TestImportSessionStoreSessionCount", "TestGlobalSessionStore", "TestImportSession"]

## INVEST Criteria
- **Independent**: Executed in isolated task branch without modifying shared backlog on branch.
- **Negotiable**: Concrete boundaries derived from AST seams.
- **Valuable**: Retires grandfathered technical debt from `.specops/grandfathered_debt.json`.
- **Estimable**: Symbol-level decomposition blueprint provided.
- **Small (<500 lines)**: Target submodules each strictly under 400 lines.
- **Testable**: Validated via blackbox frontdoor tests (ADR-0003).
