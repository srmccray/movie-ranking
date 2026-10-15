---
id: '0016'
title: 'app/routers/analytics.py: de-duplicate the genre aggregation and move GENRE_MAP
  to app/constants/genres.py'
status: Complete
governing_adrs:
- ADR-0002
- ADR-0003
governing_prds:
- PRD-0006
governing_stories:
- US-0007
target_bc: backend
---

# TASK-0016: app/routers/analytics.py: de-duplicate the genre aggregation and move GENRE_MAP to app/constants/genres.py

## Summary
`app/routers/analytics.py` is 436 lines (over the 400-line warning shown by `spec-ops health`) and repeats the same rolling-year query and primary-genre counting in two places. Extract the shared pieces and move the genre lookup table out so the file drops below 400 lines with no change to any response.

Priority: P2. Size: S. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- Duplication: `get_genres` (`app/routers/analytics.py:131-199`) and `_get_top_genre` (`:250-318`) both compute `today = date.today()`, `start_date = date(today.year - 1, today.month, 1)`, `end_date = today` (lines 148-151 and 267-269), run the same `select(Ranking).options(joinedload(Ranking.movie)).where(user_id, cast(rated_at, Date) >= start, <= end)` query (156-163 and 272-281), then count the first `genre_ids` entry per movie into a `defaultdict(int)` (170-176 and 291-297). `get_stats` calls `_get_top_genre`, so `/stats/` runs the query a second time.
- Extract private helpers in a new module `app/routers/analytics_helpers.py` or in `app/services/analytics_genres.py` (pick one; do not leave them in `analytics.py`): `rolling_year_window(today) -> tuple[date, date]`, `fetch_year_rankings(db, user_id, start, end) -> list[Ranking]`, `primary_genre_counts(rankings) -> dict[int, int]` (and ratings per genre for `get_genres`). Both endpoints use them. Preserve tie-breaking in `_get_top_genre`: highest count, then alphabetical name.
- `GENRE_MAP` (`analytics.py:29-49`, 19 TMDB ids; note it uses `"Sci-Fi"` where the dropped `genres` seed in migration 004 said `"Science Fiction"`: keep the `GENRE_MAP` strings because the frontend and tests expect them) moves to a new `app/constants/__init__.py` + `app/constants/genres.py` (`GENRE_MAP`, plus a `genre_name(genre_id)` helper returning `f"Unknown ({genre_id})"` for unknown ids, replacing the two inline `.get(...)` fallbacks at lines 179 and 304).
- Leave `cast(Ranking.rated_at, Date)` predicates as they are; rewriting them as range predicates belongs with the datetime work (TASK-0020). Optional follow-up only: aggregate in SQL on `genre_ids[1]`.

## Notes and Risks
- Do not change response shapes (`GenreResponse`, `StatsResponse`) or the rolling-year rule; `tests/test_analytics.py` must pass unmodified (same test count).
- Dependency order with TASK-0011: that task only drops the unused table; `GENRE_MAP` is untouched there, so no conflict.
- This also keeps `analytics.py` well clear of the 500-line limit before more analytics land (ADR-0002).

## Definition of Done
- [ ] `wc -l app/routers/analytics.py` is below 400 and `spec-ops health` no longer lists `analytics.py` among the proactive refactoring warnings.
- [ ] `get_genres` and `_get_top_genre` share one window helper, one fetch helper and one counting helper (no duplicated query or counting loop remains).
- [ ] `GENRE_MAP` lives in `app/constants/genres.py` and is imported from there; the `Unknown (<id>)` fallback exists once.
- [ ] `venv/bin/pytest tests/test_analytics.py` passes with the same number of collected tests, and the full suite passes.

```gherkin
Scenario: Refactoring analytics preserves genre statistics
  Given a user with rankings across several primary genres in the last year
  When the user calls GET /api/v1/analytics/genres/ and GET /api/v1/analytics/stats/
  Then the genre counts, average ratings and top genre are identical to the values before the refactor
  And app/routers/analytics.py is under 400 lines
```

## INVEST Criteria
- **Independent**: No task dependencies; executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Removes the copy-pasted query and counting loop and keeps the file under the size warning; PRD-0006, US-0007.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Small: one focused PR, a few files, well under 500 lines of change.
- **Testable**: Existing blackbox analytics tests (`tests/test_analytics.py`) assert the observable output (ADR-0003).
