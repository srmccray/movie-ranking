/** Movie handlers: TMDB search, movie creation, rankings and analytics. */

import { http, HttpResponse } from 'msw';
import { MOCK_TMDB_RESULTS, movies, rankings, tmdbServiceError } from './state';

export const movieHandlers = [
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
];
