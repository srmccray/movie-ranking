/**
 * MSW request handlers for mocking API endpoints in tests.
 *
 * These handlers simulate the backend API behavior for:
 * - Authentication (login, register)
 * - Movies (create, search)
 * - Rankings (list, create)
 */

import { http, HttpResponse } from 'msw';

// Mock data
const MOCK_TOKEN = 'mock-jwt-token-for-testing';
const MOCK_USER_EMAIL = 'test@example.com';
const MOCK_USER_PASSWORD = 'password123';

// Mock TMDB search results
const MOCK_TMDB_RESULTS = [
  {
    tmdb_id: 603,
    title: 'The Matrix',
    year: 1999,
    poster_url: 'https://image.tmdb.org/t/p/w185/abc123.jpg',
    overview: 'A computer hacker learns about the true nature of reality.',
    genre_ids: [28, 878],
    vote_average: 8.7,
    vote_count: 24000,
    release_date: '1999-03-30',
    original_language: 'en',
  },
  {
    tmdb_id: 604,
    title: 'The Matrix Reloaded',
    year: 2003,
    poster_url: 'https://image.tmdb.org/t/p/w185/def456.jpg',
    overview: 'Neo continues his mission to save humanity.',
    genre_ids: [28, 878],
    vote_average: 7.0,
    vote_count: 12000,
    release_date: '2003-05-15',
    original_language: 'en',
  },
  {
    tmdb_id: 605,
    title: 'The Matrix Revolutions',
    year: 2003,
    poster_url: 'https://image.tmdb.org/t/p/w185/ghi789.jpg',
    overview: 'The epic conclusion to the Matrix trilogy.',
    genre_ids: [28, 878],
    vote_average: 6.7,
    vote_count: 10000,
    release_date: '2003-11-05',
    original_language: 'en',
  },
];

// Store registered users for testing
const registeredUsers = new Map<string, string>();
registeredUsers.set(MOCK_USER_EMAIL, MOCK_USER_PASSWORD);

// Mock Google OAuth state
const MOCK_GOOGLE_STATE = 'mock-google-oauth-state-123';
const MOCK_GOOGLE_AUTH_URL = `https://accounts.google.com/o/oauth2/v2/auth?client_id=test&redirect_uri=http://localhost:8000/api/v1/auth/google/callback/&response_type=code&scope=openid%20email%20profile&state=${MOCK_GOOGLE_STATE}`;

// Store valid states for testing
const validOAuthStates = new Set<string>();
validOAuthStates.add(MOCK_GOOGLE_STATE);

// Store link states (for account linking flow)
const validLinkStates = new Set<string>();

// Track if user has Google linked
let userHasGoogleLinked = false;

// Store movies for testing
const movies = new Map<string, { id: string; title: string; year: number | null; tmdb_id?: number | null; poster_url?: string | null }>();

// Store rankings for testing
const rankings = new Map<string, { id: string; movie_id: string; rating: number }>();

// Flag to simulate TMDB service errors
let tmdbServiceError: 'rate_limit' | 'api_error' | 'unavailable' | null = null;

export const handlers = [
  // POST /api/v1/auth/register
  http.post('/api/v1/auth/register', async ({ request }) => {
    const contentType = request.headers.get('Content-Type');

    // Registration should use JSON
    if (!contentType?.includes('application/json')) {
      return HttpResponse.json(
        { detail: 'Content-Type must be application/json' },
        { status: 415 }
      );
    }

    const body = (await request.json()) as { email?: string; password?: string };

    if (!body.email || !body.password) {
      return HttpResponse.json(
        { detail: 'Email and password are required' },
        { status: 422 }
      );
    }

    // Check if email is already registered
    if (registeredUsers.has(body.email)) {
      return HttpResponse.json(
        { detail: 'Email already registered' },
        { status: 409 }
      );
    }

    // Register the user
    registeredUsers.set(body.email, body.password);

    return HttpResponse.json(
      {
        access_token: MOCK_TOKEN,
        token_type: 'bearer',
      },
      { status: 201 }
    );
  }),

  // POST /api/v1/auth/login
  http.post('/api/v1/auth/login', async ({ request }) => {
    const contentType = request.headers.get('Content-Type');

    // Login MUST use form-urlencoded (this was the bug!)
    if (!contentType?.includes('application/x-www-form-urlencoded')) {
      return HttpResponse.json(
        {
          detail: [
            {
              loc: ['body'],
              msg: 'Expected form-urlencoded data',
              type: 'value_error',
            },
          ],
        },
        { status: 422 }
      );
    }

    const formData = await request.text();
    const params = new URLSearchParams(formData);
    const username = params.get('username');
    const password = params.get('password');

    if (!username || !password) {
      return HttpResponse.json(
        { detail: 'Username and password are required' },
        { status: 422 }
      );
    }

    // Check credentials
    const storedPassword = registeredUsers.get(username);
    if (!storedPassword || storedPassword !== password) {
      return HttpResponse.json(
        { detail: 'Invalid email or password' },
        { status: 401 }
      );
    }

    return HttpResponse.json({
      access_token: MOCK_TOKEN,
      token_type: 'bearer',
    });
  }),

  // GET /api/v1/movies/search/
  http.get('/api/v1/movies/search/', ({ request }) => {
    const authHeader = request.headers.get('Authorization');

    if (!authHeader?.startsWith('Bearer ')) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }

    // Check for simulated errors
    if (tmdbServiceError === 'rate_limit') {
      return HttpResponse.json(
        { detail: 'TMDB rate limit exceeded. Please try again later.' },
        { status: 503 }
      );
    }
    if (tmdbServiceError === 'api_error') {
      return HttpResponse.json(
        { detail: 'Failed to search TMDB. Please try again.' },
        { status: 500 }
      );
    }
    if (tmdbServiceError === 'unavailable') {
      return HttpResponse.json(
        { detail: 'TMDB service unavailable. Please try again later.' },
        { status: 500 }
      );
    }

    const url = new URL(request.url);
    const query = url.searchParams.get('q');
    const year = url.searchParams.get('year');

    if (!query || query.trim() === '') {
      return HttpResponse.json(
        {
          detail: [
            {
              loc: ['query', 'q'],
              msg: 'Field required',
              type: 'missing',
            },
          ],
        },
        { status: 422 }
      );
    }

    // Filter results based on query and year
    let results = MOCK_TMDB_RESULTS.filter((movie) =>
      movie.title.toLowerCase().includes(query.toLowerCase())
    );

    if (year) {
      const yearNum = parseInt(year);
      results = results.filter((movie) => movie.year === yearNum);
    }

    // Return wrapped response to match backend schema
    return HttpResponse.json({
      results,
      query,
      year: year ? parseInt(year) : null,
    });
  }),

  // POST /api/v1/movies/
  http.post('/api/v1/movies/', async ({ request }) => {
    const authHeader = request.headers.get('Authorization');

    if (!authHeader?.startsWith('Bearer ')) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }

    const body = (await request.json()) as {
      title?: string;
      year?: number;
      tmdb_id?: number;
      poster_url?: string;
    };

    if (!body.title) {
      return HttpResponse.json(
        { detail: 'Title is required' },
        { status: 422 }
      );
    }

    const movie = {
      id: `movie-${Date.now()}`,
      title: body.title,
      year: body.year || null,
      tmdb_id: body.tmdb_id || null,
      poster_url: body.poster_url || null,
      created_at: new Date().toISOString(),
    };

    movies.set(movie.id, movie);

    return HttpResponse.json(movie, { status: 201 });
  }),

  // POST /api/v1/rankings/
  http.post('/api/v1/rankings/', async ({ request }) => {
    const authHeader = request.headers.get('Authorization');

    if (!authHeader?.startsWith('Bearer ')) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }

    const body = (await request.json()) as { movie_id?: string; rating?: number };

    if (!body.movie_id || body.rating === undefined) {
      return HttpResponse.json(
        { detail: 'movie_id and rating are required' },
        { status: 422 }
      );
    }

    // Check if movie exists
    if (!movies.has(body.movie_id)) {
      return HttpResponse.json(
        { detail: 'Movie not found' },
        { status: 404 }
      );
    }

    const ranking = {
      id: `ranking-${Date.now()}`,
      movie_id: body.movie_id,
      rating: body.rating,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    rankings.set(ranking.id, ranking);

    return HttpResponse.json(ranking, { status: 201 });
  }),

  // GET /api/v1/rankings/
  http.get('/api/v1/rankings/', ({ request }) => {
    const authHeader = request.headers.get('Authorization');

    if (!authHeader?.startsWith('Bearer ')) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }

    const url = new URL(request.url);
    const limit = parseInt(url.searchParams.get('limit') || '20');
    const offset = parseInt(url.searchParams.get('offset') || '0');

    const allRankings = Array.from(rankings.values());
    const items = allRankings.slice(offset, offset + limit).map((ranking) => {
      const movie = movies.get(ranking.movie_id);
      return {
        id: ranking.id,
        rating: ranking.rating,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        movie: movie
          ? { id: movie.id, title: movie.title, year: movie.year, poster_url: movie.poster_url || null }
          : null,
      };
    });

    return HttpResponse.json({
      items,
      total: allRankings.length,
      limit,
      offset,
    });
  }),

  // GET /api/v1/analytics/stats/
  http.get('/api/v1/analytics/stats/', ({ request }) => {
    const authHeader = request.headers.get('Authorization');

    if (!authHeader?.startsWith('Bearer ')) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }

    // Calculate mock stats from rankings
    const allRankings = Array.from(rankings.values());
    const totalMovies = allRankings.length;

    // Calculate average rating
    const averageRating = totalMovies > 0
      ? allRankings.reduce((sum, r) => sum + r.rating, 0) / totalMovies
      : 0;

    // Calculate total watch time (mock: assume 120 min per movie)
    const totalWatchTimeMinutes = totalMovies * 120;

    return HttpResponse.json({
      total_movies: totalMovies,
      total_watch_time_minutes: totalWatchTimeMinutes,
      average_rating: Math.round(averageRating * 100) / 100,
      current_streak: 0,
      longest_streak: 0,
    });
  }),

  // GET /api/v1/analytics/rating-distribution/
  http.get('/api/v1/analytics/rating-distribution/', ({ request }) => {
    const authHeader = request.headers.get('Authorization');

    if (!authHeader?.startsWith('Bearer ')) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }

    // Count ratings from rankings
    const allRankings = Array.from(rankings.values());
    const ratingCounts: Record<number, number> = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };

    for (const ranking of allRankings) {
      if (ranking.rating >= 1 && ranking.rating <= 5) {
        ratingCounts[ranking.rating]++;
      }
    }

    const distribution = [1, 2, 3, 4, 5].map((rating) => ({
      rating,
      count: ratingCounts[rating],
    }));

    const total = allRankings.length;

    return HttpResponse.json({
      distribution,
      total,
    });
  }),

  // GET /api/v1/auth/google/login/
  http.get('/api/v1/auth/google/login/', () => {
    // Generate a new state and store it
    const newState = `state-${Date.now()}`;
    validOAuthStates.add(newState);

    return HttpResponse.json({
      authorization_url: `https://accounts.google.com/o/oauth2/v2/auth?client_id=test&redirect_uri=http://localhost:8000/api/v1/auth/google/callback/&response_type=code&scope=openid%20email%20profile&state=${newState}`,
    });
  }),

  // GET /api/v1/auth/google/callback/
  http.get('/api/v1/auth/google/callback/', ({ request }) => {
    const url = new URL(request.url);
    const code = url.searchParams.get('code');
    const state = url.searchParams.get('state');
    const error = url.searchParams.get('error');

    // Handle user cancellation
    if (error) {
      return HttpResponse.json(
        { detail: 'Authentication cancelled' },
        { status: 400 }
      );
    }

    // Check for missing parameters
    if (!code || !state) {
      return HttpResponse.json(
        { detail: 'Missing required parameters' },
        { status: 400 }
      );
    }

    // Validate state (CSRF protection)
    if (!validOAuthStates.has(state)) {
      return HttpResponse.json(
        { detail: 'Invalid or expired authentication state' },
        { status: 400 }
      );
    }

    // Remove used state
    validOAuthStates.delete(state);

    // Return mock token
    return HttpResponse.json({
      access_token: MOCK_TOKEN,
      token_type: 'bearer',
    });
  }),

  // GET /api/v1/auth/me/
  http.get('/api/v1/auth/me/', ({ request }) => {
    const authHeader = request.headers.get('Authorization');

    if (!authHeader?.startsWith('Bearer ')) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }

    return HttpResponse.json({
      id: 'user-123',
      email: MOCK_USER_EMAIL,
      auth_provider: userHasGoogleLinked ? 'linked' : 'local',
      has_google_linked: userHasGoogleLinked,
      has_password: true,
      created_at: '2024-01-01T00:00:00Z',
    });
  }),

  // GET /api/v1/auth/google/link/
  http.get('/api/v1/auth/google/link/', ({ request }) => {
    const authHeader = request.headers.get('Authorization');

    if (!authHeader?.startsWith('Bearer ')) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }

    // Check if already linked
    if (userHasGoogleLinked) {
      return HttpResponse.json(
        { detail: 'Google account already linked' },
        { status: 409 }
      );
    }

    // Generate a link state
    const linkState = `link-state-${Date.now()}`;
    validLinkStates.add(linkState);

    return HttpResponse.json({
      authorization_url: `https://accounts.google.com/o/oauth2/v2/auth?client_id=test&redirect_uri=http://localhost:3000/settings&response_type=code&scope=openid%20email%20profile&state=${linkState}`,
    });
  }),
];

// Helper to reset mock data between tests
export function resetMockData() {
  registeredUsers.clear();
  registeredUsers.set(MOCK_USER_EMAIL, MOCK_USER_PASSWORD);
  movies.clear();
  rankings.clear();
  tmdbServiceError = null;
  validOAuthStates.clear();
  validOAuthStates.add(MOCK_GOOGLE_STATE);
  validLinkStates.clear();
  userHasGoogleLinked = false;
  importSessions.clear();
}

// Helper to simulate TMDB service errors
export function setTmdbServiceError(error: 'rate_limit' | 'api_error' | 'unavailable' | null) {
  tmdbServiceError = error;
}

// Helper to add a valid OAuth state for testing
export function addValidOAuthState(state: string) {
  validOAuthStates.add(state);
}

// Helper to set Google linked status for testing
export function setUserGoogleLinked(linked: boolean) {
  userHasGoogleLinked = linked;
}

// ============================================
// Amazon Prime Import Mock Data and Handlers
// ============================================

// Mock import session data
interface MockImportSession {
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

const importSessions = new Map<string, MockImportSession>();

// Mock import session for testing
const MOCK_IMPORT_SESSION: MockImportSession = {
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

// Add import handlers to main handlers array
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

// Export mock constants for use in tests
export { MOCK_TOKEN, MOCK_USER_EMAIL, MOCK_USER_PASSWORD, MOCK_TMDB_RESULTS, MOCK_GOOGLE_STATE, MOCK_GOOGLE_AUTH_URL, MOCK_IMPORT_SESSION };
