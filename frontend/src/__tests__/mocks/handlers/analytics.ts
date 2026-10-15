/** Analytics handlers: stats, rating distribution, activity and genres. */

import { http, HttpResponse } from 'msw';
import { rankings } from './state';

export const analyticsHandlers = [
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

  // GET /api/v1/analytics/activity/
  http.get('/api/v1/analytics/activity/', ({ request }) => {
    const authHeader = request.headers.get('Authorization');

    if (!authHeader?.startsWith('Bearer ')) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }

    const end = new Date();
    const start = new Date(end);
    start.setUTCDate(start.getUTCDate() - 365);
    const day = (d: Date) => d.toISOString().slice(0, 10);

    return HttpResponse.json({
      activity: [],
      start_date: day(start),
      end_date: day(end),
    });
  }),

  // GET /api/v1/analytics/genres/
  http.get('/api/v1/analytics/genres/', ({ request }) => {
    const authHeader = request.headers.get('Authorization');

    if (!authHeader?.startsWith('Bearer ')) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }

    return HttpResponse.json({
      genres: [],
      total_movies: 0,
    });
  }),
];
