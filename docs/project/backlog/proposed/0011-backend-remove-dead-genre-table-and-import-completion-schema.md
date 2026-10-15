---
id: '0011'
title: 'app/models + alembic: remove the unused Genre model and genres table, and the unused ImportCompletionResponse schema'
status: Proposed
governing_adrs:
- ADR-0002
- ADR-0003
governing_prds:
- PRD-0006
governing_stories:
- US-0007
dependencies: []
target_bc: backend
priority: P2
---

# TASK-0011: app/models + alembic: remove the unused Genre model and genres table, and the unused ImportCompletionResponse schema

## Summary
Two pieces of backend code are never used: the `Genre` model with its `genres` table (genre names come from the hard-coded `GENRE_MAP` in `app/routers/analytics.py`) and the `ImportCompletionResponse` schema (no endpoint returns it). The product owner decided to delete them rather than wire them up. Remove both, drop the table with a new migration, and update the docs that mention them.

Priority: P2. Size: S. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- **Genre**: `app/models/genre.py` (34 lines); imported in `app/models/__init__.py:3` and exported in `__all__` at line 9. Nothing else references it (`grep -rn "Genre\b" app tests` finds only those). The table is created and seeded in `alembic/versions/004_add_movie_metadata.py` (`op.create_table("genres", ...)` at line 34, seed at lines 102-132, dropped in `downgrade` at line 146). **Do not edit 004.** Add `alembic/versions/007_drop_genres_table.py` with `down_revision = "006_oauth_linking"` (the current head, revision id in `006_add_oauth_state_linking_fields.py:18`): `upgrade` drops `genres`; `downgrade` recreates it with the same columns (`id` integer PK without autoincrement, `name` string) and reseeds the same rows as 004 so a downgrade is lossless.
- **ImportCompletionResponse**: defined at `app/schemas/import_amazon.py:165`; imported at `app/schemas/__init__.py:4` and listed in `__all__` at line 41. No router or test uses it (`grep -rn ImportCompletionResponse app tests frontend/src` finds only these, plus the sentence in `app/CLAUDE.md:792`). Delete the class and both references, and delete the last sentence of `app/CLAUDE.md:792` (`ImportCompletionResponse exists in the schemas but no endpoint currently returns it.`).
- Check `app/CLAUDE.md` and `frontend/CLAUDE.md` for other mentions of the `genres` table or `Genre` model and remove them (the TMDB genre-name mapping is `GENRE_MAP`, which stays).

## Notes and Risks
- Migration numbering: this is the first of several new migrations. Keep the order 007 (this) -> TASK-0020 (008) -> TASK-0024 (009) -> TASK-0025 (010) -> TASK-0026 (011) to avoid multiple Alembic heads; the dependencies on those tasks encode it. If two branches land out of order, rebase and fix `down_revision`.
- Production has no readers of `genres`, so dropping it is safe; still take a backup before the first production migration run.
- Models are also imported by `alembic/env.py` (`from app import models`), so removing the import changes autogenerate output; verify `alembic upgrade head` on a scratch database.

## Definition of Done
- [ ] `app/models/genre.py` no longer exists and `grep -rn "Genre\b" app/` returns nothing.
- [ ] `grep -rn ImportCompletionResponse app/ tests/ frontend/src` returns nothing, and `app/CLAUDE.md` no longer mentions it.
- [ ] `alembic/versions/007_drop_genres_table.py` exists, `alembic upgrade head` removes the `genres` table, and `alembic downgrade -1` recreates it with 19 seed rows (verify on PostgreSQL or via TASK-0018 once it lands).
- [ ] `venv/bin/pytest` passes with the same number of collected tests as before.

```gherkin
Scenario: Removing dead code does not change behavior
  Given the Genre model and ImportCompletionResponse are removed and migration 007 is applied
  When the full backend suite runs with `venv/bin/pytest`
  Then every previously collected test still passes
  And the genres table no longer exists in the database
```

## INVEST Criteria
- **Independent**: No task dependencies; executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Removes unreferenced code and a table nothing reads; the decision to delete rather than wire up was made by the product owner. PRD-0006, US-0007.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Small: one focused PR, a few files, well under 500 lines of change.
- **Testable**: Pytest suite unchanged; migration verified with `alembic upgrade head`/`downgrade -1` (ADR-0003 plus ADR-0007).
