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
    id: 603,
    title: 'The Matrix',
    year: 1999,
    poster_url: 'https://image.tmdb.org/t/p/w185/abc123.jpg',
    overview: 'A computer hacker learns about the true nature of reality.',
  },
  {
    id: 604,
    title: 'The Matrix Reloaded',
    year: 2003,
    poster_url: 'https://image.tmdb.org/t/p/w185/def456.jpg',
    overview: 'Neo continues his mission to save humanity.',
  },
  {
    id: 605,
    title: 'The Matrix Revolutions',
    year: 2003,
    poster_url: 'https://image.tmdb.org/t/p/w185/ghi789.jpg',
    overview: 'The epic conclusion to the Matrix trilogy.',
  },
];

// Store registered users for testing
const registeredUsers = new Map<string, string>();
registeredUsers.set(MOCK_USER_EMAIL, MOCK_USER_PASSWORD);

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

    return HttpResponse.json(results);
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
          ? { id: movie.id, title: movie.title, year: movie.year }
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
];

// Helper to reset mock data between tests
export function resetMockData() {
  registeredUsers.clear();
  registeredUsers.set(MOCK_USER_EMAIL, MOCK_USER_PASSWORD);
  movies.clear();
  rankings.clear();
  tmdbServiceError = null;
}

// Helper to simulate TMDB service errors
export function setTmdbServiceError(error: 'rate_limit' | 'api_error' | 'unavailable' | null) {
  tmdbServiceError = error;
}

// Export mock constants for use in tests
export { MOCK_TOKEN, MOCK_USER_EMAIL, MOCK_USER_PASSWORD, MOCK_TMDB_RESULTS };
