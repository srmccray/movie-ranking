import { Button } from './Button';
import type { UseImportMovieSearchResult } from '../hooks/useImportMovieSearch';

type SearchState = Pick<
  UseImportMovieSearchResult,
  | 'searchQuery'
  | 'setSearchQuery'
  | 'searchResults'
  | 'isSearching'
  | 'searchError'
  | 'highlightedIndex'
  | 'setHighlightedIndex'
  | 'hasSearched'
  | 'inputRef'
  | 'resultsRef'
  | 'handleSearchClose'
  | 'handleSelectMovie'
  | 'handleSearchKeyDown'
>;

interface ImportMovieSearchPanelProps extends SearchState {
  /** Title of the CSV movie being re-matched. */
  movieTitle: string;
  isProcessing: boolean;
}

/** Presentational manual-search panel shown inside ImportReview. */
export function ImportMovieSearchPanel({
  movieTitle,
  isProcessing,
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
  handleSearchClose,
  handleSelectMovie,
  handleSearchKeyDown,
}: ImportMovieSearchPanelProps) {
  return (
    <div className="import-search">
      <div className="import-search-header">
        <span className="import-search-label">
          Search for: <strong>{movieTitle}</strong>
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
  );
}
