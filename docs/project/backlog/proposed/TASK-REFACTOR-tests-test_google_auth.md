---
id: REFACTOR-tests-test_google_auth
title: Refactor and Decompose Legacy File test_google_auth.py
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

# TASK-REFACTOR-tests-test_google_auth: Refactor Legacy File test_google_auth.py

## Summary
The grandfathered debt file `tests/test_google_auth.py` contains 649 lines and violates the hard file length invariant governed by ADR-0002 (<500 lines).
This task plans the incremental extraction of cohesive submodules (test_google_auth_endpoint.py, test_google_auth_user.py) and establishes a public barrel export facade.

## Target Submodule Decomposition Path
Target decomposition destination: `tests/test_google_auth/` with submodules:
- `test_google_auth_endpoint.py`: TestGoogleLoginEndpoint, TestGoogleCallbackEndpoint, TestUserProfileEndpoint, TestGoogleLinkEndpoint, TestGoogleLinkCallbackEndpoint, TestGoogleOAuthFlow
- `test_google_auth_user.py`: TestGoogleUserCanStillUsePassword, TestGoogleOnlyUserCannotUsePassword

## AST Decomposition Blueprint
Decomposition Blueprint for /Users/stephen/Projects/movie-ranking/tests/test_google_auth.py (649 lines):
  Submodule 'test_google_auth_endpoint.py' (~542 lines):
    - [class] TestGoogleLoginEndpoint (lines 18-64)
    - [class] TestGoogleCallbackEndpoint (lines 67-119)
    - [class] TestUserProfileEndpoint (lines 356-392)
    - [class] TestGoogleLinkEndpoint (lines 395-474)
    - [class] TestGoogleLinkCallbackEndpoint (lines 477-649)
    - [class] TestGoogleOAuthFlow (lines 122-273)
  Submodule 'test_google_auth_user.py' (~76 lines):
    - [class] TestGoogleUserCanStillUsePassword (lines 276-313)
    - [class] TestGoogleOnlyUserCannotUsePassword (lines 316-353)
  Suggested barrel exports:
    from .test_google_auth_endpoint import TestGoogleLoginEndpoint, TestGoogleCallbackEndpoint, TestUserProfileEndpoint, TestGoogleLinkEndpoint, TestGoogleLinkCallbackEndpoint, TestGoogleOAuthFlow
    from .test_google_auth_user import TestGoogleUserCanStillUsePassword, TestGoogleOnlyUserCannotUsePassword
    
    __all__ = ["TestGoogleLoginEndpoint", "TestGoogleCallbackEndpoint", "TestUserProfileEndpoint", "TestGoogleLinkEndpoint", "TestGoogleLinkCallbackEndpoint", "TestGoogleOAuthFlow", "TestGoogleUserCanStillUsePassword", "TestGoogleOnlyUserCannotUsePassword"]

## INVEST Criteria
- **Independent**: Executed in isolated task branch without modifying shared backlog on branch.
- **Negotiable**: Concrete boundaries derived from AST seams.
- **Valuable**: Retires grandfathered technical debt from `.specops/grandfathered_debt.json`.
- **Estimable**: Symbol-level decomposition blueprint provided.
- **Small (<500 lines)**: Target submodules each strictly under 400 lines.
- **Testable**: Validated via blackbox frontdoor tests (ADR-0003).
