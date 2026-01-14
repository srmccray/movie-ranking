import { useEffect, useState, useCallback } from 'react';
import { Header } from '../components/Header';
import { ActivityChart } from '../components/ActivityChart';
import { GenreChart } from '../components/GenreChart';
import { Button } from '../components/Button';
import { apiClient, ApiClientError } from '../api/client';
import type { ActivityResponse, GenreResponse } from '../types';

export function AnalyticsPage() {
  const [activity, setActivity] = useState<ActivityResponse | null>(null);
  const [genres, setGenres] = useState<GenreResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalytics = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [activityData, genreData] = await Promise.all([
        apiClient.getActivity(),
        apiClient.getGenres(),
      ]);
      setActivity(activityData);
      setGenres(genreData);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else {
        setError('Failed to load analytics data');
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  return (
    <>
      <Header />
      <main className="main-layout">
        <div className="container">
          <div className="page-content">
            <div className="page-header">
              <h1 className="page-title">Analytics</h1>
            </div>

            {error && (
              <div className="alert alert-error" role="alert">
                {error}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => fetchAnalytics()}
                  style={{ marginLeft: 'var(--space-2)' }}
                >
                  Retry
                </Button>
              </div>
            )}

            {isLoading && (
              <div className="loading-container">
                <div className="spinner" />
              </div>
            )}

            {!isLoading && (
              <div className="analytics-grid">
                {activity && (
                  <ActivityChart
                    activity={activity.activity}
                    startDate={activity.start_date}
                    endDate={activity.end_date}
                  />
                )}

                {genres && (
                  <GenreChart
                    genres={genres.genres}
                    totalMovies={genres.total_movies}
                  />
                )}
              </div>
            )}
          </div>
        </div>
      </main>
    </>
  );
}
