import { useEffect, useState, useCallback } from 'react';
import { Header } from '../components/Header';
import { MovieCard } from '../components/MovieCard';
import { EmptyState } from '../components/EmptyState';
import { Button } from '../components/Button';
import { Modal } from '../components/Modal';
import { AddMovieForm } from '../components/AddMovieForm';
import { AddMovieCard } from '../components/AddMovieCard';
import { useRankings } from '../hooks/useRankings';
import type { MovieCreate, SortOption } from '../types';

const SORT_OPTIONS: SortOption[] = [
  { label: 'Date (Newest)', field: 'rated_at', order: 'desc' },
  { label: 'Date (Oldest)', field: 'rated_at', order: 'asc' },
  { label: 'Rating (High to Low)', field: 'rating', order: 'desc' },
  { label: 'Rating (Low to High)', field: 'rating', order: 'asc' },
  { label: 'Title (A-Z)', field: 'title', order: 'asc' },
  { label: 'Title (Z-A)', field: 'title', order: 'desc' },
  { label: 'Year (Newest)', field: 'year', order: 'desc' },
  { label: 'Year (Oldest)', field: 'year', order: 'asc' },
];

export function RankingsPage() {
  const {
    rankings,
    total,
    isLoading,
    error,
    hasMore,
    sortBy,
    sortOrder,
    fetchRankings,
    loadMore,
    setSort,
    addMovieAndRank,
    updateRating,
    updateRatedAt,
    deleteRanking,
  } = useRankings();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [updateError, setUpdateError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Fetch rankings on mount and when sort changes
  useEffect(() => {
    fetchRankings(true);
  }, [sortBy, sortOrder]);

  const handleSortChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      const selectedOption = SORT_OPTIONS[parseInt(e.target.value, 10)];
      if (selectedOption) {
        setSort(selectedOption.field, selectedOption.order);
      }
    },
    [setSort]
  );

  // Get current sort option index
  const currentSortIndex = SORT_OPTIONS.findIndex(
    (opt) => opt.field === sortBy && opt.order === sortOrder
  );

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

  // Track if user has scrolled down enough to show back-to-top button
  const [showBackToTop, setShowBackToTop] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      // Show button after scrolling 400px
      setShowBackToTop(window.scrollY > 400);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToTop = useCallback(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

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
              {rankings.length > 0 && (
                <div className="sort-control">
                  <label htmlFor="sort-select" className="sort-label">
                    Sort by
                  </label>
                  <select
                    id="sort-select"
                    className="sort-select"
                    value={currentSortIndex >= 0 ? currentSortIndex : 0}
                    onChange={handleSortChange}
                  >
                    {SORT_OPTIONS.map((option, index) => (
                      <option key={`${option.field}-${option.order}`} value={index}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
              )}
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

                <div className="load-more">
                  {hasMore ? (
                    <>
                      <p className="load-more-progress">
                        Showing {rankings.length} of {total} movies
                      </p>
                      <Button
                        variant="secondary"
                        onClick={loadMore}
                        loading={isLoading}
                      >
                        Load More
                      </Button>
                    </>
                  ) : total > 0 && (
                    <p className="load-more-progress">
                      Showing all {total} movies
                    </p>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      </main>

      {showBackToTop && (
        <button
          className="back-to-top"
          onClick={scrollToTop}
          aria-label="Back to top"
          title="Back to top"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 15l-6-6-6 6" />
          </svg>
        </button>
      )}

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
