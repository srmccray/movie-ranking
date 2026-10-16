/**
 * Shared test support for the ImportReview / ImportWizard characterization tests.
 * Builders for import fixtures and a stateful host that plays the role ImportWizard
 * plays in production (owning the movie list), so the component under test is real.
 */

import { act } from '@testing-library/react';
import { vi, beforeAll, afterAll, beforeEach, afterEach } from 'vitest';
import { setMockSession } from '../mocks/handlers';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';
import type { MatchedMovieItem, TMDBMatchResult } from '../../types';

export const SESSION_ID = 'session-abc';

export function makeMatch(overrides: Partial<TMDBMatchResult> = {}): TMDBMatchResult {
  return {
    tmdb_id: 603,
    title: 'The Matrix',
    year: 1999,
    poster_url: 'https://image.tmdb.org/t/p/w185/matrix.jpg',
    overview: 'A computer hacker learns about the true nature of reality.',
    ...overrides,
  };
}

export function makeMovie(overrides: Partial<MatchedMovieItem> = {}): MatchedMovieItem {
  return {
    parsed: { title: 'The Matrix', watch_date: '2024-01-15T00:00:00Z', prime_image_url: null },
    tmdb_match: makeMatch(),
    confidence: 0.95,
    alternatives: [],
    status: 'pending',
    ...overrides,
  };
}

export function makeUnmatched(title = 'Unknown Movie 2024'): MatchedMovieItem {
  return makeMovie({
    parsed: { title, watch_date: null, prime_image_url: null },
    tmdb_match: null,
    confidence: 0,
  });
}

/** Three-movie list: matched, matched, unmatched. */
export function makeMovies(): MatchedMovieItem[] {
  return [
    makeMovie(),
    makeMovie({
      parsed: { title: 'Inception', watch_date: null, prime_image_url: null },
      tmdb_match: makeMatch({ tmdb_id: 27205, title: 'Inception', year: 2010, poster_url: null, overview: null }),
      confidence: 0.6,
    }),
    makeUnmatched(),
  ];
}

export function makeSearchResults(count: number) {
  return Array.from({ length: count }, (_, i) => ({
    tmdb_id: 1000 + i,
    title: `Result ${i + 1}`,
    year: 2000 + i,
    poster_url: null,
    overview: null,
    genre_ids: [],
    vote_average: 5,
    vote_count: 10,
    release_date: `${2000 + i}-01-01`,
    original_language: 'en',
  }));
}

export function makeCallbacks() {
  return {
    onAdd: vi.fn().mockResolvedValue(undefined),
    onSkip: vi.fn().mockResolvedValue(undefined),
    onComplete: vi.fn(),
    onMovieUpdated: vi.fn(),
  };
}

/**
 * Overrides GET /movies/search/ and records each requested query.
 * `respond` builds the JSON results array for a query (default: no results).
 */
export function recordSearches(respond: (q: string) => unknown[] = () => []) {
  const queries: string[] = [];
  server.use(
    http.get('/api/v1/movies/search/', ({ request }) => {
      const q = new URL(request.url).searchParams.get('q') ?? '';
      queries.push(q);
      return HttpResponse.json({ results: respond(q), query: q, year: null });
    })
  );
  return queries;
}

/**
 * Registers hooks that fake only setTimeout/clearTimeout, authenticate the API client, and stub
 * scrollIntoView. Testing Library only drains its async queue under fake timers when it detects
 * a `jest` global; Vitest has none, so the one method it calls is exposed (known RTL/Vitest workaround).
 */
export function useFakeSearchTimers() {
  beforeAll(() => {
    Object.assign(globalThis, { jest: { advanceTimersByTime: (ms: number) => vi.advanceTimersByTime(ms) } });
  });
  afterAll(() => {
    delete (globalThis as { jest?: unknown }).jest;
  });
  beforeEach(() => {
    setMockSession(true);
    Element.prototype.scrollIntoView = vi.fn();
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
  });
  afterEach(() => {
    vi.useRealTimers();
    setMockSession(false);
  });
}

/** Advance the (fake) clock and let resulting promise work settle. */
export const advance = (ms: number) =>
  act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
