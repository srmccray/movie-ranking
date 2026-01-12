import { useEffect, useState, useCallback } from 'react';
import { Header } from '../components/Header';
import { MovieCard } from '../components/MovieCard';
import { EmptyState } from '../components/EmptyState';
import { Button } from '../components/Button';
import { Modal } from '../components/Modal';
import { AddMovieForm } from '../components/AddMovieForm';
import { AddMovieCard } from '../components/AddMovieCard';
import { useRankings } from '../hooks/useRankings';
import type { MovieCreate } from '../types';

export function RankingsPage() {
  const {
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
  } = useRankings();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [updateError, setUpdateError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Fetch rankings on mount
  useEffect(() => {
    fetchRankings(true);
  }, []);

  const handleOpenModal = useCallback(() => {
    setIsModalOpen(true);
  }, []);

  const handleCloseModal = useCallback(() => {
    setIsModalOpen(false);
  }, []);

  const handleAddMovie = useCallback(
    async (movie: MovieCreate, rating: number, ratedAt?: string) => {
      await addMovieAndRank(movie, rating, ratedAt);
      setIsModalOpen(false);
    },
    [addMovieAndRank]
  );

  const handleRatingChange = useCallback(
    async (movieId: string, rating: number) => {
      setUpdateError(null);
      try {
        await updateRating(movieId, rating);
      } catch (err) {
        setUpdateError(err instanceof Error ? err.message : 'Failed to update rating');
      }
    },
    [updateRating]
  );

  const handleRatedAtChange = useCallback(
    async (rankingId: string, movieId: string, ratedAt: string) => {
      setUpdateError(null);
      try {
        await updateRatedAt(rankingId, movieId, ratedAt);
      } catch (err) {
        setUpdateError(err instanceof Error ? err.message : 'Failed to update date');
      }
    },
    [updateRatedAt]
  );

  const handleDelete = useCallback(
    async (rankingId: string) => {
      setDeleteError(null);
      try {
        await deleteRanking(rankingId);
      } catch (err) {
        setDeleteError(err instanceof Error ? err.message : 'Failed to delete ranking');
      }
    },
    [deleteRanking]
  );

  const showEmptyState = !isLoading && rankings.length === 0 && !error;
  const showRankings = rankings.length > 0;

  return (
    <>
      <Header />
      <main className="main-layout">
        <div className="container">
          <div className="page-content">
            <div className="page-header">
              <h1 className="page-title">
                My Rankings
                {total > 0 && (
                  <span style={{ fontWeight: 400, color: 'var(--color-neutral-500)', marginLeft: 'var(--space-2)' }}>
                    ({total})
                  </span>
                )}
              </h1>
            </div>

            {error && (
              <div className="alert alert-error" role="alert">
                {error}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => fetchRankings(true)}
                  style={{ marginLeft: 'var(--space-2)' }}
                >
                  Retry
                </Button>
              </div>
            )}

            {updateError && (
              <div className="alert alert-error" role="alert">
                {updateError}
              </div>
            )}

            {deleteError && (
              <div className="alert alert-error" role="alert">
                {deleteError}
              </div>
            )}

            {isLoading && rankings.length === 0 && (
              <div className="loading-container">
                <div className="spinner" />
              </div>
            )}

            {showEmptyState && (
              <EmptyState
                title="No movies ranked yet"
                description="Start by adding a movie and giving it a rating."
                action={{
                  label: 'Add Your First Movie',
                  onClick: handleOpenModal,
                }}
              />
            )}

            {showRankings && (
              <>
                <div className="rankings-list">
                  <AddMovieCard onClick={handleOpenModal} />
                  {rankings.map((ranking) => (
                    <MovieCard
                      key={ranking.id}
                      ranking={ranking}
                      onRatingChange={handleRatingChange}
                      onRatedAtChange={handleRatedAtChange}
                      onDelete={handleDelete}
                    />
                  ))}
                </div>

                {hasMore && (
                  <div className="load-more">
                    <Button
                      variant="secondary"
                      onClick={loadMore}
                      loading={isLoading}
                    >
                      Load More
                    </Button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </main>

      <Modal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        title="Add New Movie"
      >
        <AddMovieForm onSubmit={handleAddMovie} onCancel={handleCloseModal} />
      </Modal>
    </>
  );
}
