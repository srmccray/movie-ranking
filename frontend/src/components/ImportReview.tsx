import { useState, useCallback } from 'react';
import { Button } from './Button';
import { StarRating } from './StarRating';
import { ImportMovieSearchPanel } from './ImportMovieSearchPanel';
import { ApiClientError } from '../api/client';
import { useImportMovieSearch } from '../hooks/useImportMovieSearch';
import type { MatchedMovieItem } from '../types';

interface ImportReviewProps {
  movies: MatchedMovieItem[];
  currentIndex: number;
  sessionId: string;
  onAdd: (rating: number, ratedAt?: string) => Promise<void>;
  onSkip: () => Promise<void>;
  onComplete: () => void;
  onMovieUpdated: (index: number, updatedMovie: MatchedMovieItem) => void;
}


export function ImportReview({
  movies,
  currentIndex,
  sessionId,
  onAdd,
  onSkip,
  onComplete,
  onMovieUpdated,
}: ImportReviewProps) {
  const [rating, setRating] = useState<number>(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);


  const currentMovie = movies[currentIndex];

  const {
    isSearchMode,
    searchQuery,
    setSearchQuery,
    searchResults,
    isSearching,
    searchError,
    highlightedIndex,
    setHighlightedIndex,
    hasSearched,
    inputRef,
    resultsRef,
    handleSearchOpen,
    handleSearchClose,
    handleSelectMovie,
    handleSearchKeyDown,
  } = useImportMovieSearch({
    currentMovie,
    sessionId,
    currentIndex,
    onMovieUpdated,
    setIsProcessing,
    setError,
  });

  const pendingMovies = movies.filter(m => m.status === 'pending');
  const progress = ((movies.length - pendingMovies.length) / movies.length) * 100;

  const handleAdd = useCallback(async () => {
    if (rating === 0) {
      setError('Please select a rating');
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      // Use watch_date from CSV as rated_at if available
      const ratedAt = currentMovie.parsed.watch_date || undefined;
      await onAdd(rating, ratedAt);
      setRating(0); // Reset for next movie
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else {
        setError('Failed to add movie');
      }
    } finally {
      setIsProcessing(false);
    }
  }, [rating, currentMovie, onAdd]);

  const handleSkip = useCallback(async () => {
    setIsProcessing(true);
    setError(null);

    try {
      await onSkip();
      setRating(0);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else {
        setError('Failed to skip movie');
      }
    } finally {
      setIsProcessing(false);
    }
  }, [onSkip]);

  if (!currentMovie) {
    return (
      <div className="import-review-empty">
        <p>No more movies to review.</p>
        <Button onClick={onComplete}>Finish Import</Button>
      </div>
    );
  }

  const movie = currentMovie.tmdb_match ?? null;
  const isUnmatched = movie === null;
  const confidenceLabel = currentMovie.confidence >= 0.7 ? 'High' :
                          currentMovie.confidence >= 0.5 ? 'Medium' : 'Low';

  return (
    <div className="import-review">
      {/* Progress Bar */}
      <div className="import-review-progress">
        <div className="import-review-progress-bar">
          <div
            className="import-review-progress-fill"
            style={{ width: `${progress}%` }}
          />
        </div>
        <span className="import-review-progress-text">
          {currentIndex + 1} of {movies.length}
        </span>
      </div>

      {/* Search Mode UI */}
      {isSearchMode && (
        <ImportMovieSearchPanel
          movieTitle={currentMovie.parsed.title}
          isProcessing={isProcessing}
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          searchResults={searchResults}
          isSearching={isSearching}
          searchError={searchError}
          highlightedIndex={highlightedIndex}
          setHighlightedIndex={setHighlightedIndex}
          hasSearched={hasSearched}
          inputRef={inputRef}
          resultsRef={resultsRef}
          handleSearchClose={handleSearchClose}
          handleSelectMovie={handleSelectMovie}
          handleSearchKeyDown={handleSearchKeyDown}
        />
      )}

      {/* Movie Card */}
      {!isSearchMode && (
      <div className="import-review-card">
        {isUnmatched ? (
          <div className="import-review-unmatched">
            <div className="import-review-unmatched-title">
              No match found for:
            </div>
            <div className="import-review-unmatched-name">
              {currentMovie.parsed.title}
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleSearchOpen}
              disabled={isProcessing}
            >
              Search for this movie
            </Button>
          </div>
        ) : (
          <>
            <div className="import-review-poster">
              {movie.poster_url ? (
                <img
                  src={movie.poster_url}
                  alt={`${movie.title} poster`}
                  className="import-review-poster-image"
                />
              ) : (
                <div className="import-review-poster-placeholder">
                  No Poster
                </div>
              )}
            </div>
            <div className="import-review-info">
              <h3 className="import-review-title">{movie.title}</h3>
              {movie.year && (
                <span className="import-review-year">{movie.year}</span>
              )}
              {movie.overview && (
                <p className="import-review-overview">{movie.overview}</p>
              )}
              <div className="import-review-confidence">
                <span className={`import-review-confidence-badge confidence-${confidenceLabel.toLowerCase()}`}>
                  {confidenceLabel} confidence match
                </span>
                <button
                  type="button"
                  className="import-review-search-link"
                  onClick={handleSearchOpen}
                  disabled={isProcessing}
                >
                  Search for different movie
                </button>
              </div>
              {currentMovie.parsed.watch_date && (
                <div className="import-review-watch-date">
                  Watched: {new Date(currentMovie.parsed.watch_date).toLocaleDateString('en-US', { timeZone: 'UTC' })}
                </div>
              )}
            </div>
          </>
        )}
      </div>
      )}

      {/* Rating Input */}
      {!isSearchMode && !isUnmatched && (
        <div className="import-review-rating">
          <label className="import-review-rating-label">Your Rating:</label>
          <StarRating
            value={rating}
            onChange={setRating}
            size="lg"
          />
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      )}

      {/* Actions */}
      {!isSearchMode && (
        <div className="import-review-actions">
          <Button
            variant="ghost"
            onClick={handleSkip}
            disabled={isProcessing}
          >
            Skip
          </Button>
          {!isUnmatched && (
            <Button
              onClick={handleAdd}
              disabled={isProcessing || rating === 0}
              loading={isProcessing}
            >
              Add to My Movies
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
