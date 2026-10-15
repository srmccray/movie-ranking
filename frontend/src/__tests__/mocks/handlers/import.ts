import { http, HttpResponse } from 'msw';
// ============================================
// Amazon Prime Import Mock Data and Handlers
// ============================================

// Mock import session data
export interface MockImportSession {
  session_id: string;
  movies: Array<{
    parsed: {
      title: string;
      watch_date: string | null;
      prime_image_url: string | null;
    };
    tmdb_match: {
      tmdb_id: number;
      title: string;
      year: number | null;
      poster_url: string | null;
      overview: string | null;
    } | null;
    confidence: number;
    alternatives: Array<{
      tmdb_id: number;
      title: string;
      year: number | null;
      poster_url: string | null;
      overview: string | null;
    }>;
    status: 'pending' | 'added' | 'skipped';
  }>;
  total_entries: number;
  movies_found: number;
  tv_shows_filtered: number;
  already_ranked: number;
}

export const importSessions = new Map<string, MockImportSession>();

// Mock import session for testing
export const MOCK_IMPORT_SESSION: MockImportSession = {
  session_id: 'mock-import-session-123',
  movies: [
    {
      parsed: {
        title: 'The Matrix',
        watch_date: '2024-01-15T00:00:00Z',
        prime_image_url: 'https://prime.example.com/matrix.jpg',
      },
      tmdb_match: {
        tmdb_id: 603,
        title: 'The Matrix',
        year: 1999,
        poster_url: 'https://image.tmdb.org/t/p/w185/matrix.jpg',
        overview: 'A computer hacker learns about the true nature of reality.',
      },
      confidence: 0.95,
      alternatives: [
        {
          tmdb_id: 604,
          title: 'The Matrix Reloaded',
          year: 2003,
          poster_url: 'https://image.tmdb.org/t/p/w185/matrix2.jpg',
          overview: 'Neo continues his mission.',
        },
      ],
      status: 'pending',
    },
    {
      parsed: {
        title: 'Inception',
        watch_date: '2024-01-20T00:00:00Z',
        prime_image_url: null,
      },
      tmdb_match: {
        tmdb_id: 27205,
        title: 'Inception',
        year: 2010,
        poster_url: 'https://image.tmdb.org/t/p/w185/inception.jpg',
        overview: 'A thief who steals corporate secrets through dream-sharing.',
      },
      confidence: 0.98,
      alternatives: [],
      status: 'pending',
    },
    {
      parsed: {
        title: 'Unknown Movie 2024',
        watch_date: null,
        prime_image_url: null,
      },
      tmdb_match: null,
      confidence: 0.0,
      alternatives: [],
      status: 'pending',
    },
  ],
  total_entries: 10,
  movies_found: 5,
  tv_shows_filtered: 3,
  already_ranked: 2,
};

export const importHandlers = [
  // POST /api/v1/import/amazon-prime/upload/
  http.post('/api/v1/import/amazon-prime/upload/', async ({ request }) => {
    const authHeader = request.headers.get('Authorization');

    if (!authHeader?.startsWith('Bearer ')) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }

    // Check content type is multipart/form-data
    const contentType = request.headers.get('Content-Type');
    if (!contentType?.includes('multipart/form-data')) {
      return HttpResponse.json(
        { detail: 'Expected multipart/form-data' },
        { status: 422 }
      );
    }

    // Create a new session with mock data
    const sessionId = `session-${Date.now()}`;
    const session: MockImportSession = {
      ...MOCK_IMPORT_SESSION,
      session_id: sessionId,
      movies: MOCK_IMPORT_SESSION.movies.map((m) => ({ ...m, status: 'pending' as const })),
    };
    importSessions.set(sessionId, session);

    return HttpResponse.json({
      session_id: sessionId,
      total_entries: session.total_entries,
      movies_found: session.movies_found,
      tv_shows_filtered: session.tv_shows_filtered,
      already_ranked: session.already_ranked,
      ready_for_review: session.movies.length,
      movies: session.movies,
    });
  }),

  // GET /api/v1/import/amazon-prime/session/{session_id}/
  http.get('/api/v1/import/amazon-prime/session/:sessionId/', ({ request, params }) => {
    const authHeader = request.headers.get('Authorization');

    if (!authHeader?.startsWith('Bearer ')) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }

    const { sessionId } = params;
    const session = importSessions.get(sessionId as string);

    if (!session) {
      return HttpResponse.json(
        { detail: 'Import session not found or expired' },
        { status: 404 }
      );
    }

    const addedCount = session.movies.filter((m) => m.status === 'added').length;
    const skippedCount = session.movies.filter((m) => m.status === 'skipped').length;
    const remainingCount = session.movies.filter((m) => m.status === 'pending').length;
    const currentIndex = session.movies.findIndex((m) => m.status === 'pending');

    return HttpResponse.json({
      session_id: session.session_id,
      current_index: currentIndex >= 0 ? currentIndex : session.movies.length,
      total_movies: session.movies.length,
      added_count: addedCount,
      skipped_count: skippedCount,
      remaining_count: remainingCount,
      movies: session.movies,
    });
  }),

  // POST /api/v1/import/amazon-prime/session/{session_id}/movie/{index}/add/
  http.post('/api/v1/import/amazon-prime/session/:sessionId/movie/:index/add/', async ({ request, params }) => {
    const authHeader = request.headers.get('Authorization');

    if (!authHeader?.startsWith('Bearer ')) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }

    const { sessionId, index } = params;
    const session = importSessions.get(sessionId as string);

    if (!session) {
      return HttpResponse.json(
        { detail: 'Import session not found or expired' },
        { status: 404 }
      );
    }

    const movieIndex = parseInt(index as string);
    if (movieIndex < 0 || movieIndex >= session.movies.length) {
      return HttpResponse.json(
        { detail: 'Movie index out of range' },
        { status: 404 }
      );
    }

    const movie = session.movies[movieIndex];
    if (movie.status !== 'pending') {
      return HttpResponse.json(
        { detail: 'Movie has already been processed' },
        { status: 409 }
      );
    }

    if (!movie.tmdb_match) {
      return HttpResponse.json(
        { detail: 'Cannot add movie without TMDB match' },
        { status: 422 }
      );
    }

    const body = (await request.json()) as { rating?: number; rated_at?: string };

    if (!body.rating || body.rating < 1 || body.rating > 5) {
      return HttpResponse.json(
        { detail: 'Rating must be between 1 and 5' },
        { status: 422 }
      );
    }

    // Mark as added
    movie.status = 'added';

    // Create a mock ranking
    const ranking = {
      id: `ranking-import-${Date.now()}`,
      movie_id: `movie-${movie.tmdb_match.tmdb_id}`,
      rating: body.rating,
      rated_at: body.rated_at || movie.parsed.watch_date || new Date().toISOString(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    return HttpResponse.json(ranking, { status: 201 });
  }),

  // POST /api/v1/import/amazon-prime/session/{session_id}/movie/{index}/skip/
  http.post('/api/v1/import/amazon-prime/session/:sessionId/movie/:index/skip/', ({ request, params }) => {
    const authHeader = request.headers.get('Authorization');

    if (!authHeader?.startsWith('Bearer ')) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }

    const { sessionId, index } = params;
    const session = importSessions.get(sessionId as string);

    if (!session) {
      return HttpResponse.json(
        { detail: 'Import session not found or expired' },
        { status: 404 }
      );
    }

    const movieIndex = parseInt(index as string);
    if (movieIndex < 0 || movieIndex >= session.movies.length) {
      return HttpResponse.json(
        { detail: 'Movie index out of range' },
        { status: 404 }
      );
    }

    const movie = session.movies[movieIndex];
    if (movie.status !== 'pending') {
      return HttpResponse.json(
        { detail: 'Movie has already been processed' },
        { status: 409 }
      );
    }

    // Mark as skipped
    movie.status = 'skipped';

    return new HttpResponse(null, { status: 204 });
  }),

  // DELETE /api/v1/import/amazon-prime/session/{session_id}/
  http.delete('/api/v1/import/amazon-prime/session/:sessionId/', ({ request, params }) => {
    const authHeader = request.headers.get('Authorization');

    if (!authHeader?.startsWith('Bearer ')) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }

    const { sessionId } = params;
    const session = importSessions.get(sessionId as string);

    if (!session) {
      return HttpResponse.json(
        { detail: 'Import session not found or expired' },
        { status: 404 }
      );
    }

    // Delete the session
    importSessions.delete(sessionId as string);

    return new HttpResponse(null, { status: 204 });
  }),
];

// Helper to reset import sessions between tests
export function resetImportSessions() {
  importSessions.clear();
}

// Helper to create a pre-populated import session for testing
export function createMockImportSession(): string {
  const sessionId = `test-session-${Date.now()}`;
  const session: MockImportSession = {
    ...MOCK_IMPORT_SESSION,
    session_id: sessionId,
    movies: MOCK_IMPORT_SESSION.movies.map((m) => ({ ...m, status: 'pending' as const })),
  };
  importSessions.set(sessionId, session);
  return sessionId;
}
