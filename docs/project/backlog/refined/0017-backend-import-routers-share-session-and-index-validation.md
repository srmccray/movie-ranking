---
id: '0017'
title: 'app/routers/import_amazon: share the session lookup and movie-index validation
  in one helper'
status: Refined
dependencies:
- TASK-0014
governing_adrs:
- ADR-0002
- ADR-0003
governing_prds:
- PRD-0006
governing_stories:
- US-0007
target_bc: backend
---

# TASK-0017: app/routers/import_amazon: share the session lookup and movie-index validation in one helper

## Summary
The import routers repeat the same checks: look up the user's session (404 `Import session not found or expired`), range-check the movie index (404 `Movie index out of range`) and reject already-processed movies (400). Put each check in one place so the messages and status codes cannot drift, and so TASK-0025 only has to change the lookup once.

Priority: P2. Size: S. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- Session lookup + 404 is repeated in `app/routers/import_amazon/review.py:99-105` (`add_import_movie`), `:258-264` (`skip_import_movie`), `:320-326` (`update_import_movie_match`) and `app/routers/import_amazon/session.py:138-144` (`get_import_session`), `:183-189` (`cancel_import_session`). Each calls `import_session_store.get_session(session_id, str(current_user.id))`.
- Index range check (`index < 0 or index >= len(session.movies)` -> 404 `Movie index out of range`) is repeated in `review.py:107-112`, `:266-271`, `:328-333`. The 'already processed' check (`movie_data.status != "pending"` -> 400 `Movie has already been processed`) is in `review.py:116-119` and `:274-277`. (The earlier discovery said the index error was a 400; it is a 404.)
- Add `app/routers/import_amazon/deps.py` with `get_session_or_404(session_id, user) -> ImportSession` and `get_pending_movie(session, index) -> MatchedMovieItem` (range check and processed check) and use them in all five handlers. Keep the exact status codes and `detail` strings; define the three strings once as module constants.
- Optional in the same PR if it stays small: the TMDB get-or-create block in `add_import_movie` (`review.py:127-176`) is extracted by TASK-0023; do not do it here.
- `str(current_user.id)` is passed to the store at five call sites; the helper in `deps.py` is the single place that does the conversion.

## Notes and Risks
- Pure refactor: all error strings and codes must be byte-identical; `tests/test_import_session_access.py`, `tests/test_import_amazon_review.py` and `tests/test_import_amazon_flow.py` assert them.
- TASK-0025 later replaces the in-memory store with a database-backed one; keeping `get_session_or_404` as the only caller of `get_session` makes that change one function instead of five.

## Dependencies
- TASK-0014 edits `app/routers/import_amazon/review.py` (lines 32 and 193); this task rewrites most of the same file, so it goes second to avoid conflicts.

## Definition of Done
- [ ] `grep -n "Import session not found or expired" app/` matches exactly one definition (a constant) and the handlers use the helper.
- [ ] `grep -n "Movie index out of range" app/` and `grep -n "Movie has already been processed" app/` each match exactly one definition.
- [ ] `venv/bin/pytest tests/test_import_session_access.py tests/test_import_amazon_review.py tests/test_import_amazon_flow.py` pass and the full suite passes with the same test count.
- [ ] `app/routers/import_amazon/review.py` is shorter than before and no file in the package exceeds 400 lines.

```gherkin
Scenario: Import errors are unchanged after sharing the checks
  Given an import session with 2 movies
  When a client requests movie index 5, an already-added movie, and an unknown session id
  Then the responses are 404 "Movie index out of range", 400 "Movie has already been processed" and 404 "Import session not found or expired" respectively
```

## INVEST Criteria
- **Independent**: Ordered after TASK-0014 (see Dependencies); otherwise executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: One source for three user-visible error contracts and a single seam for persisting sessions; PRD-0006, US-0007.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Small: one focused PR, a few files, well under 500 lines of change.
- **Testable**: The listed existing blackbox suites assert status codes and messages through the public endpoints (ADR-0003).
