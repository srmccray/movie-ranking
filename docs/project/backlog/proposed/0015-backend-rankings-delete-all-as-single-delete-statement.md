---
id: '0015'
title: 'app/routers/rankings.py: delete all rankings with a single DELETE statement'
status: Proposed
governing_adrs:
- ADR-0003
governing_prds:
- PRD-0006
governing_stories:
- US-0007
dependencies: []
target_bc: backend
priority: P2
---

# TASK-0015: app/routers/rankings.py: delete all rankings with a single DELETE statement

## Summary
`DELETE /api/v1/rankings/all/` loads every ranking of the user and deletes them one at a time. For a user with hundreds of rankings that is one SELECT plus one DELETE per row. Replace it with one bulk DELETE with the same response.

Priority: P2. Size: XS. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- `app/routers/rankings.py:216-240` (`delete_all_rankings`): `select(Ranking).where(Ranking.user_id == current_user.id)`, then `for ranking in rankings: await db.delete(ranking)`, then `await db.flush()`. The route is declared at line 207 (`/all/`, status 204) and must stay declared before `/{ranking_id}/` (line 255) so `all` is not parsed as a UUID.
- Replace the body with `await db.execute(delete(Ranking).where(Ranking.user_id == current_user.id))` (import `delete` from `sqlalchemy`). Keep the 204 and the 401 behavior.
- Note for later tasks: if TASK-0027 lands first, this endpoint must also delete the user's `watches` (ADR-0011 decision 3); keep this change minimal and let that task extend it.

## Notes and Risks
- A bulk Core `DELETE` skips ORM cascade events. `Ranking` has no child rows; the only ORM cascades are on the parent side (`app/models/user.py:70` and `app/models/movie.py:94`, `cascade="all, delete-orphan"` on the `rankings` collections), which matter when a user or movie is deleted, not here.
- Tests in `tests/test_rankings.py` already cover delete-all; add one assertion that other users' rankings survive if it is not covered yet.

## Definition of Done
- [ ] `delete_all_rankings` issues one DELETE statement (visible with `echo=True` or a statement counter in a test) and no per-row `db.delete`.
- [ ] `DELETE /api/v1/rankings/all/` still returns 204 and removes only the caller's rankings (another user's rankings remain).
- [ ] `venv/bin/pytest tests/test_rankings.py` passes.

```gherkin
Scenario: Deleting all rankings removes only the caller's rankings
  Given Casey has 3 rankings and another user has 2 rankings
  When Casey calls DELETE /api/v1/rankings/all/
  Then the response status is 204
  And Casey's rankings list is empty
  And the other user still has 2 rankings
```

## INVEST Criteria
- **Independent**: No task dependencies; executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Replaces N+1 deletes with one statement; PRD-0006, US-0007.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Extra small: a handful of lines in one or two files.
- **Testable**: Blackbox through `DELETE /rankings/all/` and `GET /rankings/` (ADR-0003).
