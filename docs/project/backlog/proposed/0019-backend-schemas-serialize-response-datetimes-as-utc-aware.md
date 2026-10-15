---
id: '0019'
title: 'app/schemas: serialize response datetimes as UTC-aware ISO 8601 so the column conversion cannot shift times'
status: Proposed
governing_adrs:
- ADR-0010
governing_prds:
- PRD-0006
governing_stories:
- US-0007
dependencies:
- TASK-0014
target_bc: backend
priority: P1
---

# TASK-0019: app/schemas: serialize response datetimes as UTC-aware ISO 8601 so the column conversion cannot shift times

## Summary
Today production returns timezone-aware datetimes (asyncpg reads `timestamptz`), so JSON looks like `2026-03-01T23:30:00Z`. After the columns become `timestamp without time zone` (TASK-0020) Pydantic would emit `2026-03-01T23:30:00` with no offset, and the browser parses that as local time (`new Date("2026-03-01T23:30:00")`), shifting every displayed date by the viewer's offset. Make every response datetime explicitly UTC first, in a release that is safe on both column types.

Priority: P1. Size: S. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- Response models with datetime fields: `app/schemas/ranking.py:43-45` (`RankingResponse.rated_at/created_at/updated_at`) and `:66-68` (`RankingWithMovie`), `app/schemas/movie.py:83` (`MovieResponse.created_at`), `app/schemas/user.py:35` (`UserResponse.created_at`) and `:66` (`UserProfileResponse.created_at`). Request models (`RankingCreate.rated_at` at `ranking.py:23`, import `rated_at`/`watch_date` in `app/schemas/import_amazon.py:26,162`) must keep accepting any offset and are normalized by `to_naive_utc`; do not change them. `ParsedEntry.watch_date` (`import_amazon.py:26`) comes from the CSV and is out of scope.
- Add `app/schemas/types.py` with `UTCDatetime = Annotated[datetime, AfterValidator(_as_utc)]` where `_as_utc` returns `v.replace(tzinfo=timezone.utc)` for naive values and `v.astimezone(timezone.utc)` for aware ones. Pydantic v2 serializes aware UTC datetimes as `...Z`. Use `UTCDatetime` for the five response fields above.
- This is safe before the migration (aware values stay UTC) and after it (naive values are labelled UTC), which is the reason it ships as its own task before TASK-0020.

## Notes and Risks
- SQLite tests currently receive naive datetimes, so JSON in tests changes from `2023-06-15T00:00:00` to `2023-06-15T00:00:00Z`. Existing assertions use `startswith("2023-06-15")` (`tests/test_import_amazon_review.py:101`) or key presence, so they should still pass; fix any exact-string assertion you find.
- Frontend: `MovieCard.tsx` parses `rated_at` with `new Date(dateString)` (line 52) and `toInputDateValue(rated_at)`; with `Z` suffixed values the result is unchanged from production today. No frontend change is needed; confirm in a browser.
- Do not use a custom `json_encoders` global; keep the annotated type local to the response schemas.

## Dependencies
- TASK-0014 introduces `app/utils/time.py`; the serializer reuses its UTC conventions and both touch the same CLAUDE.md datetime docs.

## Definition of Done
- [ ] `GET /api/v1/rankings/`, `GET /api/v1/auth/me/` and `POST /api/v1/movies/` return `rated_at`/`created_at`/`updated_at` strings ending in `Z` (or `+00:00`) in tests.
- [ ] A response built from a naive datetime and one built from an aware non-UTC datetime both serialize to the same instant in UTC (unit-level test through an endpoint using a ranking with an explicit offset in the request).
- [ ] Request schemas are unchanged: `POST /api/v1/rankings/` still accepts `rated_at` with `+05:00` and stores the UTC-equivalent naive value.
- [ ] `venv/bin/pytest` passes with the same collected test count.

```gherkin
Scenario: Response datetimes always carry a UTC offset
  Given Casey has a ranking rated at 2026-03-01T23:30:00 UTC
  When Casey calls GET /api/v1/rankings/
  Then rated_at is "2026-03-01T23:30:00Z"
```

## INVEST Criteria
- **Independent**: Ordered after TASK-0014 (see Dependencies); otherwise executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Prevents a user-visible timezone shift when the column types change; ADR-0010 clause 2. PRD-0006 outcome 8, US-0007.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Small: one focused PR, a few files, well under 500 lines of change.
- **Testable**: Observable in JSON responses of public endpoints (ADR-0003).
