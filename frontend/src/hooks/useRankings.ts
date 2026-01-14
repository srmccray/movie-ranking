import { useState, useCallback } from 'react';
import { apiClient, ApiClientError } from '../api/client';
import type { RankingWithMovie, RankingCreate, MovieCreate, Movie } from '../types';

interface UseRankingsReturn {
  rankings: RankingWithMovie[];
  total: number;
  isLoading: boolean;
  error: string | null;
  hasMore: boolean;
  fetchRankings: (reset?: boolean) => Promise<void>;
  loadMore: () => Promise<void>;
  addMovieAndRank: (movie: MovieCreate, rating: number, ratedAt?: string) => Promise<void>;
  updateRating: (movieId: string, rating: number) => Promise<void>;
  updateRatedAt: (rankingId: string, movieId: string, ratedAt: string) => Promise<void>;
  deleteRanking: (rankingId: string) => Promise<void>;
}

const PAGE_SIZE = 20;

export function useRankings(): UseRankingsReturn {
  const [rankings, setRankings] = useState<RankingWithMovie[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasMore = rankings.length < total;

  const fetchRankings = useCallback(async (reset = false) => {
    setIsLoading(true);
    setError(null);

    try {
      const newOffset = reset ? 0 : offset;
      const response = await apiClient.getRankings(PAGE_SIZE, newOffset);

      if (reset) {
        setRankings(response.items);
        setOffset(PAGE_SIZE);
      } else {
        setRankings((prev) => [...prev, ...response.items]);
        setOffset((prev) => prev + PAGE_SIZE);
      }
      setTotal(response.total);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else {
        setError('Failed to load rankings');
      }
    } finally {
      setIsLoading(false);
    }
  }, [offset]);

  const loadMore = useCallback(async () => {
    if (!isLoading && hasMore) {
      await fetchRankings(false);
    }
  }, [fetchRankings, isLoading, hasMore]);

  const addMovieAndRank = useCallback(
    async (movieData: MovieCreate, rating: number, ratedAt?: string) => {
      setError(null);

      try {
        // First create the movie
        const movie: Movie = await apiClient.createMovie(movieData);

        // Then create the ranking
        const rankingData: RankingCreate = {
          movie_id: movie.id,
          rating,
          // Append T00:00:00Z to interpret the date as midnight UTC, not local time
          rated_at: ratedAt ? new Date(ratedAt + 'T00:00:00Z').toISOString() : undefined,
        };
        await apiClient.createOrUpdateRanking(rankingData);

        // Refresh the rankings list
        await fetchRankings(true);
      } catch (err) {
        if (err instanceof ApiClientError) {
          throw err;
        }
        throw new Error('Failed to add movie');
      }
    },
    [fetchRankings]
  );

  const updateRating = useCallback(
    async (movieId: string, rating: number) => {
      setError(null);

      try {
        const rankingData: RankingCreate = {
          movie_id: movieId,
          rating,
        };
        await apiClient.createOrUpdateRanking(rankingData);

        // Update the local state
        setRankings((prev) =>
          prev.map((r) =>
            r.movie.id === movieId
              ? { ...r, rating, updated_at: new Date().toISOString() }
              : r
          )
        );
      } catch (err) {
        if (err instanceof ApiClientError) {
          throw err;
        }
        throw new Error('Failed to update rating');
      }
    },
    []
  );

  const updateRatedAt = useCallback(
    async (rankingId: string, movieId: string, ratedAt: string) => {
      setError(null);

      try {
        // Find the current ranking to get the current rating
        const currentRanking = rankings.find((r) => r.id === rankingId);
        if (!currentRanking) {
          throw new Error('Ranking not found');
        }

        const rankingData: RankingCreate = {
          movie_id: movieId,
          rating: currentRanking.rating,
          rated_at: ratedAt,
        };
        await apiClient.createOrUpdateRanking(rankingData);

        // Update the local state
        setRankings((prev) =>
          prev.map((r) =>
            r.id === rankingId
              ? { ...r, rated_at: ratedAt, updated_at: new Date().toISOString() }
              : r
          )
        );
      } catch (err) {
        if (err instanceof ApiClientError) {
          throw err;
        }
        throw new Error('Failed to update rated date');
      }
    },
    [rankings]
  );

  const deleteRanking = useCallback(
    async (rankingId: string) => {
      setError(null);

      try {
        await apiClient.deleteRanking(rankingId);

        // Update local state - remove the deleted ranking
        setRankings((prev) => prev.filter((r) => r.id !== rankingId));
        setTotal((prev) => prev - 1);
      } catch (err) {
        if (err instanceof ApiClientError) {
          throw err;
        }
        throw new Error('Failed to delete ranking');
      }
    },
    []
  );

  return {
    rankings,
    total,
    isLoading,
    error,
    hasMore,
    fetchRankings,
    loadMore,
    addMovieAndRank,
    updateRating,
    updateRatedAt,
    deleteRanking,
  };
}
