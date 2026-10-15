import { useState, useCallback, useEffect, useRef } from 'react';
import type { Dispatch, KeyboardEvent, RefObject, SetStateAction } from 'react';
import { apiClient, ApiClientError } from '../api/client';
import type { MatchedMovieItem, TMDBSearchResult } from '../types';

const DEBOUNCE_DELAY = 300;
const MAX_RESULTS = 10;

interface UseImportMovieSearchOptions {
  currentMovie: MatchedMovieItem | undefined;
  sessionId: string;
  currentIndex: number;
  onMovieUpdated: (index: number, updatedMovie: MatchedMovieItem) => void;
  /** Setters owned by the review component; selecting a match reports through them. */
  setIsProcessing: Dispatch<SetStateAction<boolean>>;
  setError: Dispatch<SetStateAction<string | null>>;
}

export interface UseImportMovieSearchResult {
  isSearchMode: boolean;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  searchResults: TMDBSearchResult[];
  isSearching: boolean;
  searchError: string | null;
  highlightedIndex: number;
  setHighlightedIndex: (index: number) => void;
  hasSearched: boolean;
  inputRef: RefObject<HTMLInputElement>;
  resultsRef: RefObject<HTMLUListElement>;
  handleSearchOpen: () => void;
  handleSearchClose: () => void;
  handleSelectMovie: (result: TMDBSearchResult) => Promise<void>;
  handleSearchKeyDown: (e: KeyboardEvent<HTMLInputElement>) => void;
}

/**
 * Manual TMDB re-match search for the import review step: debounced search,
 * keyboard navigation, and persisting the chosen match via the API.
 */
export function useImportMovieSearch({
  currentMovie,
  sessionId,
  currentIndex,
  onMovieUpdated,
  setIsProcessing,
  setError,
}: UseImportMovieSearchOptions): UseImportMovieSearchResult {
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
    [sessionId, currentIndex, onMovieUpdated, handleSearchClose, setIsProcessing, setError]
  );

  const handleSearchKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
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

  return {
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
  };
}
