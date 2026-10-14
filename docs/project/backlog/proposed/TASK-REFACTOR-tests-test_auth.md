---
id: REFACTOR-tests-test_auth
title: Refactor and Decompose Legacy File test_auth.py
status: Proposed
created: 2026-09-29
governing_adrs:
  - ADR-0002
target_bc: core
---

# TASK-REFACTOR-tests-test_auth: Refactor Legacy File test_auth.py

## Summary
The grandfathered debt file `tests/test_auth.py` contains 586 lines and violates the hard file length invariant governed by ADR-0002 (<500 lines).
This task plans the incremental extraction of cohesive submodules (test_auth_endpoint.py, test_auth_protected.py) and establishes a public barrel export facade.

## Target Submodule Decomposition Path
Target decomposition destination: `tests/test_auth/` with submodules:
- `test_auth_endpoint.py`: TestRegisterEndpoint, TestLoginEndpoint, TestTrailingSlashes, TestFullAuthenticationFlow, TestTokenValidation
- `test_auth_protected.py`: TestProtectedEndpoints

## AST Decomposition Blueprint
Decomposition Blueprint for /Users/stephen/Projects/movie-ranking/tests/test_auth.py (586 lines):
  Submodule 'test_auth_endpoint.py' (~475 lines):
    - [class] TestRegisterEndpoint (lines 17-135)
    - [class] TestLoginEndpoint (lines 138-303)
    - [class] TestTrailingSlashes (lines 393-424)
    - [class] TestFullAuthenticationFlow (lines 427-544)
    - [class] TestTokenValidation (lines 547-586)
  Submodule 'test_auth_protected.py' (~85 lines):
    - [class] TestProtectedEndpoints (lines 306-390)
  Suggested barrel exports:
    from .test_auth_endpoint import TestRegisterEndpoint, TestLoginEndpoint, TestTrailingSlashes, TestFullAuthenticationFlow, TestTokenValidation
    from .test_auth_protected import TestProtectedEndpoints
    
    __all__ = ["TestRegisterEndpoint", "TestLoginEndpoint", "TestTrailingSlashes", "TestFullAuthenticationFlow", "TestTokenValidation", "TestProtectedEndpoints"]

## INVEST Criteria
- **Independent**: Executed in isolated task branch without modifying shared backlog on branch.
- **Negotiable**: Concrete boundaries derived from AST seams.
- **Valuable**: Retires grandfathered technical debt from `.specops/grandfathered_debt.json`.
- **Estimable**: Symbol-level decomposition blueprint provided.
- **Small (<500 lines)**: Target submodules each strictly under 400 lines.
- **Testable**: Validated via blackbox frontdoor tests (ADR-0003).
