import { useState, useCallback, useEffect, useRef } from 'react';
import { Button } from './Button';
import { StarRating } from './StarRating';
import { apiClient, ApiClientError } from '../api/client';
import type { MatchedMovieItem, TMDBSearchResult } from '../types';

interface ImportReviewProps {
  movies: MatchedMovieItem[];
  currentIndex: number;
  sessionId: string;
  onAdd: (rating: number, ratedAt?: string) => Promise<void>;
  onSkip: () => Promise<void>;
  onComplete: () => void;
  onMovieUpdated: (index: number, updatedMovie: MatchedMovieItem) => void;
}

const DEBOUNCE_DELAY = 300;
const MAX_RESULTS = 10;

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

  // Search state
  const [isSearchMode, setIsSearchMode] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<TMDBSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const [hasSearched, setHasSearched] = useState(false);

  const inputRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLUListElement>(null);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout>>();

  const currentMovie = movies[currentIndex];
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

  // Search functionality
  const performSearch = useCallback(async (query: string) => {
    if (!query.trim()) {
      setSearchResults([]);
      setHasSearched(false);
      return;
    }

    setIsSearching(true);
    setSearchError(null);
    setHasSearched(true);

    try {
      const results = await apiClient.searchMovies(query.trim());
      setSearchResults(results.slice(0, MAX_RESULTS));
      setHighlightedIndex(-1);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setSearchError(err.message);
      } else {
        setSearchError('Failed to search movies');
      }
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  }, []);

  // Debounced search effect
  useEffect(() => {
    if (!isSearchMode) return;

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    debounceTimerRef.current = setTimeout(() => {
      performSearch(searchQuery);
    }, DEBOUNCE_DELAY);

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [searchQuery, isSearchMode, performSearch]);

  // Scroll highlighted item into view
  useEffect(() => {
    if (highlightedIndex >= 0 && resultsRef.current) {
      const items = resultsRef.current.querySelectorAll('.import-search-result');
      const highlightedItem = items[highlightedIndex] as HTMLElement;
      if (highlightedItem) {
        highlightedItem.scrollIntoView({ block: 'nearest' });
      }
    }
  }, [highlightedIndex]);

  // Focus input when entering search mode
  useEffect(() => {
    if (isSearchMode && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isSearchMode]);

  // Reset search mode when current movie changes
  useEffect(() => {
    setIsSearchMode(false);
    setSearchQuery('');
    setSearchResults([]);
    setSearchError(null);
    setHasSearched(false);
  }, [currentIndex]);

  const handleSearchOpen = useCallback(() => {
    const initialQuery = currentMovie?.parsed.title || '';
    setSearchQuery(initialQuery);
    setIsSearchMode(true);
    setSearchError(null);
    setSearchResults([]);
    setHasSearched(false);
  }, [currentMovie]);

  const handleSearchClose = useCallback(() => {
    setIsSearchMode(false);
    setSearchQuery('');
    setSearchResults([]);
    setSearchError(null);
    setHasSearched(false);
    setHighlightedIndex(-1);
  }, []);

  const handleSelectMovie = useCallback(
    async (result: TMDBSearchResult) => {
      setIsProcessing(true);
      setError(null);

      try {
        const updatedMovie = await apiClient.updateImportMovieMatch(
          sessionId,
          currentIndex,
          {
            tmdb_id: result.tmdb_id,
            title: result.title,
            year: result.year,
            poster_url: result.poster_url,
            overview: result.overview,
            genre_ids: result.genre_ids,
            vote_average: result.vote_average,
            vote_count: result.vote_count,
            release_date: result.release_date,
            original_language: result.original_language,
          }
        );
        onMovieUpdated(currentIndex, updatedMovie);
        handleSearchClose();
      } catch (err) {
        if (err instanceof ApiClientError) {
          setError(err.message);
        } else {
          setError('Failed to update movie match');
        }
      } finally {
        setIsProcessing(false);
      }
    },
    [sessionId, currentIndex, onMovieUpdated, handleSearchClose]
  );

  const handleSearchKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (searchResults.length === 0) {
        if (e.key === 'Escape') {
          e.preventDefault();
          handleSearchClose();
        }
        return;
      }

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setHighlightedIndex((prev) =>
            prev < searchResults.length - 1 ? prev + 1 : prev
          );
          break;
        case 'ArrowUp':
          e.preventDefault();
          setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : -1));
          break;
        case 'Enter':
          e.preventDefault();
          if (highlightedIndex >= 0 && highlightedIndex < searchResults.length) {
            handleSelectMovie(searchResults[highlightedIndex]);
          }
          break;
        case 'Escape':
          e.preventDefault();
          handleSearchClose();
          break;
      }
    },
    [searchResults, highlightedIndex, handleSearchClose, handleSelectMovie]
  );

  if (!currentMovie) {
    return (
      <div className="import-review-empty">
        <p>No more movies to review.</p>
        <Button onClick={onComplete}>Finish Import</Button>
      </div>
    );
  }

  const movie = currentMovie.tmdb_match;
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
        <div className="import-search">
          <div className="import-search-header">
            <span className="import-search-label">
              Search for: <strong>{currentMovie.parsed.title}</strong>
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleSearchClose}
              disabled={isProcessing}
            >
              Cancel
            </Button>
          </div>

          <div className="import-search-input-wrapper">
            <input
              ref={inputRef}
              type="text"
              className="form-input import-search-input"
              placeholder="Search for a movie..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={handleSearchKeyDown}
              aria-label="Search movies"
              aria-autocomplete="list"
              aria-controls="import-search-results"
              aria-expanded={searchResults.length > 0}
              disabled={isProcessing}
            />
            {isSearching && (
              <div className="import-search-spinner">
                <span className="spinner" aria-hidden="true" />
              </div>
            )}
          </div>

          {searchError && (
            <div className="import-search-error" role="alert">
              {searchError}
            </div>
          )}

          {hasSearched && !isSearching && searchResults.length === 0 && !searchError && searchQuery.trim() && (
            <div className="import-search-no-results">
              No movies found for "{searchQuery}"
            </div>
          )}

          {searchResults.length > 0 && (
            <ul
              ref={resultsRef}
              id="import-search-results"
              className="import-search-results"
              role="listbox"
              aria-label="Search results"
            >
              {searchResults.map((result, index) => (
                <li
                  key={result.tmdb_id}
                  className={[
                    'import-search-result',
                    highlightedIndex === index ? 'highlighted' : '',
                  ]
                    .filter(Boolean)
                    .join(' ')}
                  role="option"
                  aria-selected={highlightedIndex === index}
                  onClick={() => handleSelectMovie(result)}
                  onMouseEnter={() => setHighlightedIndex(index)}
                >
                  <div className="import-search-result-poster">
                    {result.poster_url ? (
                      <img
                        src={result.poster_url}
                        alt=""
                        className="import-search-poster-img"
                        loading="lazy"
                      />
                    ) : (
                      <div className="import-search-poster-placeholder" aria-hidden="true">
                        <svg
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.5"
                        >
                          <rect x="2" y="3" width="20" height="18" rx="2" />
                          <circle cx="8" cy="10" r="2" />
                          <path d="M21 15l-5-5L5 21" />
                        </svg>
                      </div>
                    )}
                  </div>
                  <div className="import-search-result-info">
                    <span className="import-search-result-title">{result.title}</span>
                    {result.year && (
                      <span className="import-search-result-year">{result.year}</span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
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
