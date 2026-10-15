---
id: '0014'
title: 'app/utils/time.py: add one naive-UTC helper module and replace every datetime.utcnow() call and duplicate to_naive_utc'
status: Proposed
governing_adrs:
- ADR-0010
governing_prds:
- PRD-0006
governing_stories:
- US-0007
dependencies: []
target_bc: backend
priority: P2
---

# TASK-0014: app/utils/time.py: add one naive-UTC helper module and replace every datetime.utcnow() call and duplicate to_naive_utc

## Summary
`datetime.utcnow()` (deprecated since Python 3.12) is called 11 times in `app/`, and `to_naive_utc` is copy-defined in two routers. ADR-0010 requires one helper module. Add `app/utils/time.py` with `utc_now_naive()` and `to_naive_utc()`, use them everywhere, and fix the docs that tell contributors to copy the function into each router.

Priority: P2. Size: S. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- `utcnow()` call sites in `app/` (grep `utcnow app`): `app/routers/rankings.py:109`; `app/routers/google_auth/oauth.py:35`, `:63`, `:96`; `app/routers/import_amazon/review.py:193`; `app/services/import_session.py:133`, `:169`, `:237`; model `onupdate=datetime.utcnow` at `app/models/user.py:63`, `app/models/movie.py:87`, `app/models/ranking.py:60`. (The earlier discovery counted 7; there are 11.) Tests use `utcnow` 10 times in `tests/`; replace those with the helper too.
- Duplicate converters: `app/routers/rankings.py:26` and `app/routers/import_amazon/review.py:32` (identical bodies: if `dt.tzinfo` is set, convert to UTC and drop the tzinfo). Create `app/utils/time.py` with `utc_now_naive() -> datetime` (`datetime.now(timezone.utc).replace(tzinfo=None)`) and `to_naive_utc(dt)`; delete both copies and import from the module. `rankings.py:109` and `review.py:193` use `utc_now_naive()`.
- Models: `onupdate=utc_now_naive` (a callable, not a call) in the three model files.
- Docs: root `CLAUDE.md` 'DateTime Handling' (about lines 38-56) shows the converter with the comment `# Backend conversion (app/routers/*.py)`; change to `app/utils/time.py`. `app/CLAUDE.md` lines 130, 465 and 1245-1254 show `onupdate=datetime.utcnow` and a router-local `to_naive_utc`; update them.
- Do NOT remove the tz-aware workaround at `oauth.py:97-101` here; it goes away with the column conversion in TASK-0020.

## Notes and Risks
- Behavior must be identical: both helpers return naive UTC. Comparisons between stored values and `utc_now_naive()` are unchanged on SQLite and PostgreSQL.
- Keep `to_naive_utc` importable under its old name from the router modules only if tests import it from there (`grep -rn to_naive_utc tests`); otherwise do not leave re-exports.
- The pre-commit secret scanner re-scans whole files; touching test files may resurface old fixtures. Use `# pragma: allowlist secret` on a single line if flagged (see root CLAUDE.md), never `--no-verify`.

## Definition of Done
- [ ] `grep -rn "utcnow" app/ tests/` returns nothing.
- [ ] `grep -rn "def to_naive_utc" app/` returns exactly one match, in `app/utils/time.py`.
- [ ] Root `CLAUDE.md` and `app/CLAUDE.md` reference `app/utils/time.py` instead of per-router converters and `datetime.utcnow`.
- [ ] `venv/bin/pytest` passes with the same collected test count.

```gherkin
Scenario: Time helpers are centralised
  Given app/utils/time.py provides utc_now_naive and to_naive_utc
  When the full backend suite runs
  Then it passes with the same test count
  And searching app/ for datetime.utcnow finds nothing
```

## INVEST Criteria
- **Independent**: No task dependencies; executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Removes deprecated API use and a drifting duplicated helper; first step of ADR-0010. PRD-0006, US-0007.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Small: one focused PR, a few files, well under 500 lines of change.
- **Testable**: Existing blackbox tests (ADR-0003) plus the grep checks in the Definition of Done.
