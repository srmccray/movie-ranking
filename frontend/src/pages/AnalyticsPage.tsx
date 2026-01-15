import { useEffect, useState, useCallback } from 'react';
import { Header } from '../components/Header';
import { ActivityChart } from '../components/ActivityChart';
import { GenreChart } from '../components/GenreChart';
import { StatsCard } from '../components/StatsCard';
import { RatingDistributionChart } from '../components/RatingDistributionChart';
import { Button } from '../components/Button';
import { apiClient, ApiClientError } from '../api/client';
import type {
  ActivityResponse,
  GenreResponse,
  StatsResponse,
  RatingDistributionResponse,
} from '../types';

interface LoadingState {
  activity: boolean;
  genres: boolean;
  stats: boolean;
  ratingDistribution: boolean;
}

interface ErrorState {
  activity: string | null;
  genres: string | null;
  stats: string | null;
  ratingDistribution: string | null;
}

export function AnalyticsPage() {
  const [activity, setActivity] = useState<ActivityResponse | null>(null);
  const [genres, setGenres] = useState<GenreResponse | null>(null);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [ratingDistribution, setRatingDistribution] =
    useState<RatingDistributionResponse | null>(null);

  const [loading, setLoading] = useState<LoadingState>({
    activity: true,
    genres: true,
    stats: true,
    ratingDistribution: true,
  });

  const [errors, setErrors] = useState<ErrorState>({
    activity: null,
    genres: null,
    stats: null,
    ratingDistribution: null,
  });

  const fetchAllAnalytics = useCallback(async () => {
    // Set all to loading
    setLoading({
      activity: true,
      genres: true,
      stats: true,
      ratingDistribution: true,
    });
    setErrors({
      activity: null,
      genres: null,
      stats: null,
      ratingDistribution: null,
    });

    // Fetch all 4 APIs in parallel using Promise.allSettled
    const results = await Promise.allSettled([
      apiClient.getActivity(),
      apiClient.getGenres(),
      apiClient.getStats(),
      apiClient.getRatingDistribution(),
    ]);

    // Process activity result
    if (results[0].status === 'fulfilled') {
      setActivity(results[0].value);
    } else {
      const err = results[0].reason;
      setErrors((prev) => ({
        ...prev,
        activity:
          err instanceof ApiClientError
            ? err.message
            : 'Failed to load activity data',
      }));
    }
    setLoading((prev) => ({ ...prev, activity: false }));

    // Process genres result
    if (results[1].status === 'fulfilled') {
      setGenres(results[1].value);
    } else {
      const err = results[1].reason;
      setErrors((prev) => ({
        ...prev,
        genres:
          err instanceof ApiClientError
            ? err.message
            : 'Failed to load genre data',
      }));
    }
    setLoading((prev) => ({ ...prev, genres: false }));

    // Process stats result
    if (results[2].status === 'fulfilled') {
      setStats(results[2].value);
    } else {
      const err = results[2].reason;
      setErrors((prev) => ({
        ...prev,
        stats:
          err instanceof ApiClientError
            ? err.message
            : 'Failed to load stats data',
      }));
    }
    setLoading((prev) => ({ ...prev, stats: false }));

    // Process rating distribution result
    if (results[3].status === 'fulfilled') {
      setRatingDistribution(results[3].value);
    } else {
      const err = results[3].reason;
      setErrors((prev) => ({
        ...prev,
        ratingDistribution:
          err instanceof ApiClientError
            ? err.message
            : 'Failed to load rating distribution',
      }));
    }
    setLoading((prev) => ({ ...prev, ratingDistribution: false }));
  }, []);

  useEffect(() => {
    fetchAllAnalytics();
  }, [fetchAllAnalytics]);

  const hasAnyError =
    errors.activity || errors.genres || errors.stats || errors.ratingDistribution;

  return (
    <>
      <Header />
      <main className="main-layout">
        <div className="container analytics-container">
          <div className="page-content">
            <div className="page-header">
              <h1 className="page-title">Analytics</h1>
              {hasAnyError && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => fetchAllAnalytics()}
                >
                  Retry All
                </Button>
              )}
            </div>

            <div className="analytics-dashboard">
              {/* Row 1: Activity Chart (65%) + Stats Card (35%) */}
              <div className="analytics-row analytics-row-1">
                <div className="analytics-cell">
                  {loading.activity ? (
                    <div className="activity-chart">
                      <div className="loading-container">
                        <div className="spinner" />
                      </div>
                    </div>
                  ) : errors.activity ? (
                    <div className="activity-chart">
                      <div className="analytics-card-error" role="alert">
                        <svg
                          className="analytics-card-error-icon"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                        >
                          <circle cx="12" cy="12" r="10" />
                          <line x1="12" y1="8" x2="12" y2="12" />
                          <line x1="12" y1="16" x2="12.01" y2="16" />
                        </svg>
                        <span>{errors.activity}</span>
                      </div>
                    </div>
                  ) : activity ? (
                    <ActivityChart
                      activity={activity.activity}
                      startDate={activity.start_date}
                      endDate={activity.end_date}
                    />
                  ) : null}
                </div>

                <div className="analytics-cell">
                  <StatsCard
                    totalMovies={stats?.total_movies ?? 0}
                    topGenre={stats?.top_genre ?? null}
                    averageRating={stats?.average_rating ?? 0}
                    currentStreak={stats?.current_streak ?? 0}
                    isLoading={loading.stats}
                    error={errors.stats}
                  />
                </div>
              </div>

              {/* Row 2: Genre Chart (50%) + Rating Distribution Chart (50%) */}
              <div className="analytics-row analytics-row-2">
                <div className="analytics-cell">
                  {loading.genres ? (
                    <div className="genre-chart">
                      <div className="loading-container">
                        <div className="spinner" />
                      </div>
                    </div>
                  ) : errors.genres ? (
                    <div className="genre-chart">
                      <div className="analytics-card-error" role="alert">
                        <svg
                          className="analytics-card-error-icon"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                        >
                          <circle cx="12" cy="12" r="10" />
                          <line x1="12" y1="8" x2="12" y2="12" />
                          <line x1="12" y1="16" x2="12.01" y2="16" />
                        </svg>
                        <span>{errors.genres}</span>
                      </div>
                    </div>
                  ) : genres ? (
                    <GenreChart
                      genres={genres.genres}
                      totalMovies={genres.total_movies}
                    />
                  ) : null}
                </div>

                <div className="analytics-cell">
                  <RatingDistributionChart
                    distribution={ratingDistribution?.distribution ?? []}
                    total={ratingDistribution?.total ?? 0}
                    isLoading={loading.ratingDistribution}
                    error={errors.ratingDistribution}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
