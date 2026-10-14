---
id: REFACTOR-app-routers-google_auth
title: Refactor and Decompose Legacy File google_auth.py
status: Refined
governing_adrs:
- ADR-0002
governing_prds:
- PRD-0005
governing_stories:
- US-0005
target_bc: core
---

# TASK-REFACTOR-app-routers-google_auth: Refactor Legacy File google_auth.py

## Summary
The grandfathered debt file `app/routers/google_auth.py` contains 706 lines and violates the hard file length invariant governed by ADR-0002 (<500 lines).
This task plans the incremental extraction of cohesive submodules (google_auth_token.py, google_auth_link.py) and establishes a public barrel export facade.

## Target Submodule Decomposition Path
Target decomposition destination: `app/routers/google_auth/` with submodules:
- `google_auth_token.py`: _create_state_token, _validate_state_token, _verify_google_id_token, _cleanup_expired_states, _exchange_code_for_tokens, google_login, google_callback
- `google_auth_link.py`: _handle_link_callback, google_link, google_link_callback

## AST Decomposition Blueprint
Decomposition Blueprint for /Users/stephen/Projects/movie-ranking/app/routers/google_auth.py (706 lines):
  Submodule 'google_auth_token.py' (~317 lines):
    - [function] _create_state_token (lines 47-84)
    - [function] _validate_state_token (lines 87-115)
    - [function] _verify_google_id_token (lines 153-184)
    - [function] _cleanup_expired_states (lines 37-44)
    - [function] _exchange_code_for_tokens (lines 118-150)
    - [function] google_login (lines 296-341)
    - [function] google_callback (lines 353-483)
  Submodule 'google_auth_link.py' (~298 lines):
    - [function] _handle_link_callback (lines 187-284)
    - [function] google_link (lines 497-557)
    - [function] google_link_callback (lines 568-706)
  Suggested barrel exports:
    from .google_auth_token import _create_state_token, _validate_state_token, _verify_google_id_token, _cleanup_expired_states, _exchange_code_for_tokens, google_login, google_callback
    from .google_auth_link import _handle_link_callback, google_link, google_link_callback
    
    __all__ = ["_create_state_token", "_validate_state_token", "_verify_google_id_token", "_cleanup_expired_states", "_exchange_code_for_tokens", "google_login", "google_callback", "_handle_link_callback", "google_link", "google_link_callback"]

## INVEST Criteria
- **Independent**: Executed in isolated task branch without modifying shared backlog on branch.
- **Negotiable**: Concrete boundaries derived from AST seams.
- **Valuable**: Retires grandfathered technical debt from `.specops/grandfathered_debt.json`.
- **Estimable**: Symbol-level decomposition blueprint provided.
- **Small (<500 lines)**: Target submodules each strictly under 400 lines.
- **Testable**: Validated via blackbox frontdoor tests (ADR-0003).
