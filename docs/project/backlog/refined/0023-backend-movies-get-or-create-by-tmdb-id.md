---
id: '0023'
title: 'app/routers/movies.py: make POST /api/v1/movies/ get-or-create by tmdb_id
  and share the logic with the import'
status: Refined
dependencies:
- TASK-0017
governing_adrs:
- ADR-0003
- ADR-0002
governing_prds:
- PRD-0006
governing_stories:
- US-0007
target_bc: backend
---

# TASK-0023: app/routers/movies.py: make POST /api/v1/movies/ get-or-create by tmdb_id and share the logic with the import

## Summary
`POST /api/v1/movies/` always inserts (`app/routers/movies.py:141-158`), so every user who adds the same film from TMDB search creates another `movies` row (`tmdb_id` is not unique). Rankings are unique per `(user, movie)`, so the duplicates also let one user rank the same film twice. The import path looks the film up by `tmdb_id` first (`review.py:129-130`) but uses `scalar_one_or_none()`, which raises `MultipleResultsFound` (HTTP 500) once duplicates exist. Make the create endpoint get-or-create and share one helper with the import. The partial unique index and the cleanup of existing duplicates follow in TASK-0024.

Priority: P1. Size: M. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- Current create: `app/routers/movies.py:116-158` builds a `Movie(...)` from `MovieCreate` (title, year, tmdb_id, poster_url, genre_ids, vote_average, vote_count, release_date, original_language, runtime), `db.add`, `flush`, `refresh`, returns 201.
- Current import logic: `app/routers/import_amazon/review.py:127-176` selects by `Movie.tmdb_id == tmdb_id`, creates with TMDB data and runtime from `get_movie_details` when missing, otherwise back-fills only NULL fields (`genre_ids`, `vote_average`, `vote_count`, `release_date`, `original_language`, `runtime`). `app/routers/import_amazon/matching.py:82-86` already pre-fetches existing `tmdb_id`s.
- Add `app/services/movies.py` with `find_movie_by_tmdb_id(db, tmdb_id) -> Movie | None` (use `.scalars().first()` ordered by `created_at`, `id` so pre-existing duplicates cannot raise), `create_movie(db, data) -> Movie` and `backfill_missing_metadata(movie, data) -> bool` (the NULL-only back-fill rules above).
- `POST /movies/`: when `tmdb_id` is not null, look up first; if found, back-fill missing metadata and return it with **HTTP 200**; otherwise create and return **201**. When `tmdb_id` is null (manually entered movie) always create. Set the status code through a `Response` parameter as `app/routers/rankings.py` does (`response.status_code = ...`), and add 200 to the route's `responses` documentation. `response_model=MovieResponse` is unchanged.
- `review.py` uses the same helper functions; the TMDB runtime fetch (`get_movie_details`) stays in the router because it is an external call.
- Docs: `app/CLAUDE.md` movie endpoint section and the root `CLAUDE.md` status code table note (`POST /movies/` returns 201 on create and 200 when the TMDB id already exists). Frontend `apiClient.createMovie` accepts any 2xx, so no client change; update the MSW `POST /movies/` handler only if a test needs it.

## Notes and Risks
- This task is safe before the unique index exists, and is deliberately shipped first so no new duplicates are created while the cleanup in TASK-0024 is prepared.
- A concurrent double-submit can still insert two rows until the index exists; TASK-0024 adds the `IntegrityError` retry.
- Existing tests in `tests/test_movies_create.py` assert 201 for creation; add tests for the 200 path (same `tmdb_id` twice returns the same `id`) and for `tmdb_id = null` always creating.

## Dependencies
- TASK-0017 rewrites most of `app/routers/import_amazon/review.py`, which this task also edits (the get-or-create block at lines 127-176); do it second to avoid conflicts.

## Definition of Done
- [ ] Posting the same `tmdb_id` twice returns status 201 then 200 and the same movie `id`; the second response back-fills only fields that were null.
- [ ] Posting two movies without `tmdb_id` creates two rows (both 201).
- [ ] `add_import_movie` no longer raises when two `movies` rows share a `tmdb_id` (it picks the oldest).
- [ ] The movie lookup and creation logic exists once, in `app/services/movies.py`, and both routers use it.
- [ ] `venv/bin/pytest` passes; `app/CLAUDE.md` documents the 200/201 behavior.

```gherkin
Scenario: A film is stored once
  Given Casey and another user each add the film with TMDB id 603 through POST /api/v1/movies/
  When both requests complete
  Then both responses contain the same movie id
  And the first response status is 201 and the second is 200
```

## INVEST Criteria
- **Independent**: Ordered after TASK-0017 (see Dependencies); otherwise executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Stops new duplicate films and the import crash they cause; PRD-0006 outcome 7, US-0007.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Medium: one PR touching several files; keep it under about 500 lines of changed source (excluding generated files and migrations' SQL boilerplate).
- **Testable**: Blackbox through `POST /movies/` and `GET /rankings/` (ADR-0003).
