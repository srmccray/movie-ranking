# Task Breakdown: Amazon Prime Movie History Import

**FRD:** `.claude_docs/features/amazon-prime-import/frd.md`
**Refinement:** `.claude_docs/features/amazon-prime-import/refinement.md`
**Created:** 2026-01-17
**Status:** Not Started

---

## Summary

Enable users to upload a CSV export of their Amazon Prime Video watch history, automatically match movies against TMDB, and selectively add them to their rankings through a step-by-step review workflow.

**Total Tasks:** 6
**Estimated Complexity:** Medium (6.5/10)

---

## Task Overview

| # | Task | Agent | Status | Blocked By |
|---|------|-------|--------|------------|
| 01 | Backend Schemas and Session Storage | backend-implementation | Not Started | - |
| 02 | CSV Parser Service | backend-implementation | Not Started | 01 |
| 03 | Import Router and Endpoints | backend-implementation | Not Started | 01, 02 |
| 04 | Frontend API Client and Types | frontend-implementation | Not Started | 03 |
| 05 | Import Wizard Components | frontend-implementation | Not Started | 04 |
| 06 | Backend Integration Tests | test-coverage | Not Started | 03 |

**Status Legend:**
- Not Started
- In Progress
- Complete
- Blocked
- Cancelled

---

## Dependency Graph

```
task-01 (Backend Schemas & Session Storage)
    |
    +---> task-02 (CSV Parser Service)
    |         |
    |         +---> task-03 (Import Router & Endpoints)
    |                   |
    |                   +---> task-04 (Frontend API Client & Types)
    |                   |         |
    |                   |         +---> task-05 (Import Wizard Components)
    |                   |
    |                   +---> task-06 (Backend Integration Tests)
```

---

## Critical Path

1. task-01 -> task-02 -> task-03 -> task-04 -> task-05 (longest path to user-visible feature)

---

## Parallel Opportunities

- task-04 (Frontend API Client) and task-06 (Backend Tests) can run in parallel after task-03 completes
- Frontend scaffolding (types, basic component structure) could begin while backend work is in progress, but full implementation requires API endpoints

---

## Lateral Moves (Prerequisites)

None required. All dependencies exist in the codebase:
- TMDBService for movie matching
- Rankings router for creating rankings
- Movies router for creating movies
- SettingsPage for integration point
- Modal component for wizard container

---

## Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Session Storage | In-memory dict with TTL | Matches existing OAuth state pattern, simple for single-server deployment |
| TMDB Rate Limiting | 1-second delay every 35 requests | Stay under free tier limit (40 req/10s), leverage existing error handling |
| Match Confidence | Title similarity (0.6) + Year match (0.4) | Balances accuracy with simplicity |
| New import while active | Replace existing session | Simpler UX; user intent is to start fresh |
| Watch date usage | Default rated_at to CSV watch date | More meaningful for users |

---

## Files to Create

| File | Task | Purpose |
|------|------|---------|
| `/Users/stephen/Projects/movie-ranking/app/schemas/import_amazon.py` | 01 | Request/response schemas for import |
| `/Users/stephen/Projects/movie-ranking/app/services/import_session.py` | 01 | Session storage management |
| `/Users/stephen/Projects/movie-ranking/app/services/csv_parser.py` | 02 | CSV parsing service |
| `/Users/stephen/Projects/movie-ranking/app/routers/import_amazon.py` | 03 | Import endpoints |
| `/Users/stephen/Projects/movie-ranking/frontend/src/components/ImportWizard.tsx` | 05 | Multi-step wizard container |
| `/Users/stephen/Projects/movie-ranking/frontend/src/components/ImportFileUpload.tsx` | 05 | File upload step |
| `/Users/stephen/Projects/movie-ranking/frontend/src/components/ImportReview.tsx` | 05 | Movie review step |
| `/Users/stephen/Projects/movie-ranking/frontend/src/components/ImportComplete.tsx` | 05 | Completion summary |
| `/Users/stephen/Projects/movie-ranking/tests/test_import_amazon.py` | 06 | Integration tests |

## Files to Modify

| File | Task | Changes |
|------|------|---------|
| `/Users/stephen/Projects/movie-ranking/app/main.py` | 03 | Register import router |
| `/Users/stephen/Projects/movie-ranking/frontend/src/api/client.ts` | 04 | Add import API methods |
| `/Users/stephen/Projects/movie-ranking/frontend/src/types/index.ts` | 04 | Add import types |
| `/Users/stephen/Projects/movie-ranking/frontend/src/components/index.ts` | 05 | Export new components |
| `/Users/stephen/Projects/movie-ranking/frontend/src/pages/SettingsPage.tsx` | 05 | Add Import section |

---

## Progress Log

| Date | Task | Update |
|------|------|--------|
| 2026-01-17 | - | Task breakdown created |
