import { useState, useEffect, useRef, useCallback } from 'react';
import { apiClient, ApiClientError } from '../api/client';
import type { TMDBSearchResult } from '../types';

interface MovieSearchProps {
  onSelect: (result: TMDBSearchResult) => void;
}

const DEBOUNCE_DELAY = 300;
const MAX_RESULTS = 10;

export function MovieSearch({ onSelect }: MovieSearchProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<TMDBSearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const [hasSearched, setHasSearched] = useState(false);

  const inputRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLUListElement>(null);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout>>();

  // Perform the search
  const performSearch = useCallback(async (searchQuery: string) => {
    if (!searchQuery.trim()) {
      setResults([]);
      setHasSearched(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    setHasSearched(true);

    try {
      const searchResults = await apiClient.searchMovies(searchQuery.trim());
      setResults(searchResults.slice(0, MAX_RESULTS));
      setHighlightedIndex(-1);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else {
        setError('Failed to search movies');
      }
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Debounced search effect
  useEffect(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    debounceTimerRef.current = setTimeout(() => {
      performSearch(query);
    }, DEBOUNCE_DELAY);

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [query, performSearch]);

  // Scroll highlighted item into view
  useEffect(() => {
    if (highlightedIndex >= 0 && resultsRef.current) {
      const items = resultsRef.current.querySelectorAll('.movie-search-result');
      const highlightedItem = items[highlightedIndex] as HTMLElement;
      if (highlightedItem) {
        highlightedItem.scrollIntoView({ block: 'nearest' });
      }
    }
  }, [highlightedIndex]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (results.length === 0) return;

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setHighlightedIndex((prev) =>
            prev < results.length - 1 ? prev + 1 : prev
          );
          break;
        case 'ArrowUp':
          e.preventDefault();
          setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : -1));
          break;
        case 'Enter':
          e.preventDefault();
          if (highlightedIndex >= 0 && highlightedIndex < results.length) {
            onSelect(results[highlightedIndex]);
          }
          break;
        case 'Escape':
          e.preventDefault();
          setResults([]);
          setHighlightedIndex(-1);
          break;
      }
    },
    [results, highlightedIndex, onSelect]
  );

  const handleResultClick = useCallback(
    (result: TMDBSearchResult) => {
      onSelect(result);
    },
    [onSelect]
  );

  const handleResultMouseEnter = useCallback((index: number) => {
    setHighlightedIndex(index);
  }, []);

  const showResults = results.length > 0;
  const showNoResults = hasSearched && !isLoading && results.length === 0 && !error && query.trim();

  return (
    <div className="movie-search">
      <div className="movie-search-input-wrapper">
        <input
          ref={inputRef}
          type="text"
          className="form-input movie-search-input"
          placeholder="Search for a movie..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          aria-label="Search movies"
          aria-autocomplete="list"
          aria-controls="movie-search-results"
          aria-expanded={showResults}
          autoFocus
        />
        {isLoading && (
          <div className="movie-search-spinner">
            <span className="spinner" aria-hidden="true" />
          </div>
        )}
      </div>

      {error && (
        <div className="movie-search-error" role="alert">
          {error}
        </div>
      )}

      {showNoResults && (
        <div className="movie-search-no-results">
          No movies found for "{query}"
        </div>
      )}

      {showResults && (
        <ul
          ref={resultsRef}
          id="movie-search-results"
          className="movie-search-results"
          role="listbox"
          aria-label="Search results"
        >
          {results.map((result, index) => (
            <li
              key={result.id}
              className={[
                'movie-search-result',
                highlightedIndex === index ? 'highlighted' : '',
              ]
                .filter(Boolean)
                .join(' ')}
              role="option"
              aria-selected={highlightedIndex === index}
              onClick={() => handleResultClick(result)}
              onMouseEnter={() => handleResultMouseEnter(index)}
            >
              <div className="movie-search-result-poster">
                {result.poster_url ? (
                  <img
                    src={result.poster_url}
                    alt=""
                    className="movie-search-poster-img"
                    loading="lazy"
                  />
                ) : (
                  <div className="movie-search-poster-placeholder" aria-hidden="true">
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
              <div className="movie-search-result-info">
                <span className="movie-search-result-title">{result.title}</span>
                {result.year && (
                  <span className="movie-search-result-year">{result.year}</span>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
