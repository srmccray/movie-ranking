---
id: REFACTOR-frontend-__tests__-mocks-handlers
title: Refactor and Decompose Legacy File handlers.ts
status: Refined
governing_adrs:
- ADR-0002
governing_prds:
- PRD-0005
governing_stories:
- US-0005
target_bc: core
---

# TASK-REFACTOR-frontend-__tests__-mocks-handlers: Refactor Legacy File handlers.ts

## Summary
The grandfathered debt file `frontend/src/__tests__/mocks/handlers.ts` contains 894 lines and violates the hard file length invariant governed by ADR-0002 (<500 lines).
This task plans the incremental extraction of cohesive submodules (handlers_auth.ts, handlers_session.ts) and establishes a public barrel export facade.

## Target Submodule Decomposition Path
Target decomposition destination: `frontend/src/__tests__/mocks/handlers/` with submodules:
- `handlers_auth.ts`: validOAuthStates, authHeader, authHeader, authHeader, authHeader, authHeader, authHeader, authHeader, authHeader, addValidOAuthState, authHeader, authHeader, authHeader, authHeader, authHeader, MOCK_TOKEN, MOCK_USER_EMAIL, MOCK_USER_PASSWORD, MOCK_TMDB_RESULTS, registeredUsers, MOCK_GOOGLE_STATE, MOCK_GOOGLE_AUTH_URL, validLinkStates, movies, rankings, handlers, contentType, body, contentType, formData, params, username, password, storedPassword, url, query, year, yearNum, body, movie, body, ranking, url, limit, offset, allRankings, items, movie, allRankings, totalMovies, averageRating, totalWatchTimeMinutes, allRankings, ratingCounts, distribution, total, newState, url, code, state, error, linkState, resetMockData, setTmdbServiceError, setUserGoogleLinked, importSessions, importHandlers, contentType, addedCount, skippedCount, remainingCount, currentIndex, movieIndex, movie, body, ranking, movieIndex, movie, resetImportSessions
- `handlers_session.ts`: MockImportSession, MOCK_IMPORT_SESSION, sessionId, session, session, session, session, session, createMockImportSession, sessionId, session

## AST Decomposition Blueprint
Decomposition Blueprint for /Users/stephen/Projects/movie-ranking/frontend/src/__tests__/mocks/handlers.ts (894 lines):
  Submodule 'handlers_auth.ts' (~79 lines):
    - [const] validOAuthStates (lines 66-66)
    - [const] authHeader (lines 175-175)
    - [const] authHeader (lines 243-243)
    - [const] authHeader (lines 282-282)
    - [const] authHeader (lines 323-323)
    - [const] authHeader (lines 360-360)
    - [const] authHeader (lines 392-392)
    - [const] authHeader (lines 478-478)
    - [const] authHeader (lines 499-499)
    - [function] addValidOAuthState (lines 546-546)
    - [const] authHeader (lines 661-661)
    - [const] authHeader (lines 701-701)
    - [const] authHeader (lines 738-738)
    - [const] authHeader (lines 807-807)
    - [const] authHeader (lines 850-850)
    - [const] MOCK_TOKEN (lines 13-13)
    - [const] MOCK_USER_EMAIL (lines 14-14)
    - [const] MOCK_USER_PASSWORD (lines 15-15)
    - [const] MOCK_TMDB_RESULTS (lines 18-18)
    - [const] registeredUsers (lines 58-58)
    - [const] MOCK_GOOGLE_STATE (lines 62-62)
    - [const] MOCK_GOOGLE_AUTH_URL (lines 63-63)
    - [const] validLinkStates (lines 70-70)
    - [const] movies (lines 76-76)
    - [const] rankings (lines 79-79)
    - [const] handlers (lines 84-84)
    - [const] contentType (lines 87-87)
    - [const] body (lines 97-97)
    - [const] contentType (lines 128-128)
    - [const] formData (lines 146-146)
    - [const] params (lines 147-147)
    - [const] username (lines 148-148)
    - [const] password (lines 149-149)
    - [const] storedPassword (lines 159-159)
    - [const] url (lines 204-204)
    - [const] query (lines 205-205)
    - [const] year (lines 206-206)
    - [const] yearNum (lines 229-229)
    - [const] body (lines 252-252)
    - [const] movie (lines 266-266)
    - [const] body (lines 291-291)
    - [const] ranking (lines 308-308)
    - [const] url (lines 332-332)
    - [const] limit (lines 333-333)
    - [const] offset (lines 334-334)
    - [const] allRankings (lines 336-336)
    - [const] items (lines 337-337)
    - [const] movie (lines 338-338)
    - [const] allRankings (lines 370-370)
    - [const] totalMovies (lines 371-371)
    - [const] averageRating (lines 374-374)
    - [const] totalWatchTimeMinutes (lines 379-379)
    - [const] allRankings (lines 402-402)
    - [const] ratingCounts (lines 403-403)
    - [const] distribution (lines 411-411)
    - [const] total (lines 416-416)
    - [const] newState (lines 427-427)
    - [const] url (lines 437-437)
    - [const] code (lines 438-438)
    - [const] state (lines 439-439)
    - [const] error (lines 440-440)
    - [const] linkState (lines 517-517)
    - [function] resetMockData (lines 527-527)
    - [function] setTmdbServiceError (lines 541-541)
    - [function] setUserGoogleLinked (lines 551-551)
    - [const] importSessions (lines 591-591)
    - [const] importHandlers (lines 658-658)
    - [const] contentType (lines 671-671)
    - [const] addedCount (lines 720-720)
    - [const] skippedCount (lines 721-721)
    - [const] remainingCount (lines 722-722)
    - [const] currentIndex (lines 723-723)
    - [const] movieIndex (lines 757-757)
    - [const] movie (lines 765-765)
    - [const] body (lines 780-780)
    - [const] ranking (lines 793-793)
    - [const] movieIndex (lines 826-826)
    - [const] movie (lines 834-834)
    - [function] resetImportSessions (lines 877-877)
  Submodule 'handlers_session.ts' (~11 lines):
    - [interface] MockImportSession (lines 560-560)
    - [const] MOCK_IMPORT_SESSION (lines 594-594)
    - [const] sessionId (lines 680-680)
    - [const] session (lines 681-681)
    - [const] session (lines 711-711)
    - [const] session (lines 748-748)
    - [const] session (lines 817-817)
    - [const] session (lines 860-860)
    - [function] createMockImportSession (lines 882-882)
    - [const] sessionId (lines 883-883)
    - [const] session (lines 884-884)
  Suggested barrel exports:
    export * from "./handlers_auth";
    export * from "./handlers_session";

## INVEST Criteria
- **Independent**: Executed in isolated task branch without modifying shared backlog on branch.
- **Negotiable**: Concrete boundaries derived from AST seams.
- **Valuable**: Retires grandfathered technical debt from `.specops/grandfathered_debt.json`.
- **Estimable**: Symbol-level decomposition blueprint provided.
- **Small (<500 lines)**: Target submodules each strictly under 400 lines.
- **Testable**: Validated via blackbox frontdoor tests (ADR-0003).
