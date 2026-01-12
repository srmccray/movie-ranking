import { useState, useCallback } from 'react';
import { Input } from './Input';
import { Button } from './Button';
import { StarRating } from './StarRating';
import { MovieSearch } from './MovieSearch';
import type { MovieCreate, TMDBSearchResult } from '../types';

interface AddMovieFormProps {
  onSubmit: (movie: MovieCreate, rating: number, ratedAt?: string) => Promise<void>;
  onCancel: () => void;
}

interface FormErrors {
  title?: string;
  year?: string;
  rating?: string;
}

type FormMode = 'search' | 'manual' | 'selected';

function getTodayString(): string {
  return new Date().toISOString().split('T')[0];
}

export function AddMovieForm({ onSubmit, onCancel }: AddMovieFormProps) {
  const [mode, setMode] = useState<FormMode>('search');
  const [title, setTitle] = useState('');
  const [year, setYear] = useState('');
  const [tmdbId, setTmdbId] = useState<number | null>(null);
  const [posterUrl, setPosterUrl] = useState<string | null>(null);
  // New metadata fields
  const [genreIds, setGenreIds] = useState<number[] | null>(null);
  const [voteAverage, setVoteAverage] = useState<number | null>(null);
  const [voteCount, setVoteCount] = useState<number | null>(null);
  const [releaseDate, setReleaseDate] = useState<string | null>(null);
  const [originalLanguage, setOriginalLanguage] = useState<string | null>(null);
  // Rating fields
  const [rating, setRating] = useState(0);
  const [ratedAt, setRatedAt] = useState(getTodayString());
  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const validate = (): boolean => {
    const newErrors: FormErrors = {};

    if (!title.trim()) {
      newErrors.title = 'Title is required';
    }

    if (year) {
      const yearNum = parseInt(year, 10);
      if (isNaN(yearNum) || yearNum < 1888 || yearNum > 2031) {
        newErrors.year = 'Year must be between 1888 and 2031';
      }
    }

    if (rating === 0) {
      newErrors.rating = 'Please select a rating';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);

    if (!validate()) {
      return;
    }

    setIsSubmitting(true);

    try {
      const movieData: MovieCreate = {
        title: title.trim(),
        year: year ? parseInt(year, 10) : null,
        tmdb_id: tmdbId,
        poster_url: posterUrl,
        genre_ids: genreIds,
        vote_average: voteAverage,
        vote_count: voteCount,
        release_date: releaseDate,
        original_language: originalLanguage,
      };

      await onSubmit(movieData, rating, ratedAt);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to add movie');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSearchSelect = useCallback((result: TMDBSearchResult) => {
    setTitle(result.title);
    setYear(result.year ? result.year.toString() : '');
    setTmdbId(result.tmdb_id);
    setPosterUrl(result.poster_url);
    // Set new metadata fields from search result
    setGenreIds(result.genre_ids ?? null);
    setVoteAverage(result.vote_average ?? null);
    setVoteCount(result.vote_count ?? null);
    setReleaseDate(result.release_date ?? null);
    setOriginalLanguage(result.original_language ?? null);
    setMode('selected');
    setErrors({});
  }, []);

  const handleSwitchToManual = useCallback(() => {
    setMode('manual');
    setTitle('');
    setYear('');
    setTmdbId(null);
    setPosterUrl(null);
    setGenreIds(null);
    setVoteAverage(null);
    setVoteCount(null);
    setReleaseDate(null);
    setOriginalLanguage(null);
    setErrors({});
  }, []);

  const handleSwitchToSearch = useCallback(() => {
    setMode('search');
    setTitle('');
    setYear('');
    setTmdbId(null);
    setPosterUrl(null);
    setGenreIds(null);
    setVoteAverage(null);
    setVoteCount(null);
    setReleaseDate(null);
    setOriginalLanguage(null);
    setErrors({});
  }, []);

  const handleClearSelection = useCallback(() => {
    setMode('search');
    setTitle('');
    setYear('');
    setTmdbId(null);
    setPosterUrl(null);
    setGenreIds(null);
    setVoteAverage(null);
    setVoteCount(null);
    setReleaseDate(null);
    setOriginalLanguage(null);
    setRating(0);
    setErrors({});
  }, []);

  // Search mode: show movie search
  if (mode === 'search') {
    return (
      <div className="add-movie-form">
        {submitError && (
          <div className="alert alert-error" role="alert">
            {submitError}
          </div>
        )}

        <MovieSearch onSelect={handleSearchSelect} />

        <div className="mode-switch">
          <button
            type="button"
            className="mode-switch-link"
            onClick={handleSwitchToManual}
          >
            Enter manually
          </button>
        </div>

        <div className="form-actions">
          <Button
            type="button"
            variant="secondary"
            onClick={onCancel}
            fullWidth
          >
            Cancel
          </Button>
        </div>
      </div>
    );
  }

  // Selected mode: show selected movie with confirmation
  if (mode === 'selected') {
    return (
      <form onSubmit={handleSubmit} className="add-movie-form">
        {submitError && (
          <div className="alert alert-error" role="alert">
            {submitError}
          </div>
        )}

        <div className="selected-movie">
          <div className="selected-movie-poster">
            {posterUrl ? (
              <img
                src={posterUrl}
                alt={`${title} poster`}
                className="selected-movie-poster-img"
              />
            ) : (
              <div className="selected-movie-poster-placeholder" aria-hidden="true">
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
          <div className="selected-movie-info">
            <h3 className="selected-movie-title">{title}</h3>
            {year && <p className="selected-movie-year">{year}</p>}
            <button
              type="button"
              className="mode-switch-link"
              onClick={handleClearSelection}
            >
              Choose different movie
            </button>
          </div>
        </div>

        <Input
          label="Date Rated"
          type="date"
          value={ratedAt}
          onChange={setRatedAt}
          max={getTodayString()}
        />

        <div className="form-group">
          <label className="form-label">Your Rating</label>
          <StarRating value={rating} onChange={setRating} size="lg" />
          {errors.rating && (
            <p className="form-error" role="alert">
              {errors.rating}
            </p>
          )}
        </div>

        <div className="form-actions-row">
          <Button
            type="button"
            variant="secondary"
            onClick={onCancel}
            disabled={isSubmitting}
            fullWidth
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            loading={isSubmitting}
            fullWidth
          >
            Add Movie
          </Button>
        </div>
      </form>
    );
  }

  // Manual mode: show full form
  return (
    <form onSubmit={handleSubmit} className="add-movie-form">
      {submitError && (
        <div className="alert alert-error" role="alert">
          {submitError}
        </div>
      )}

      <Input
        label="Movie Title"
        type="text"
        value={title}
        onChange={setTitle}
        error={errors.title}
        placeholder="Enter movie title"
        required
        autoFocus
      />

      <Input
        label="Year (optional)"
        type="number"
        value={year}
        onChange={setYear}
        error={errors.year}
        placeholder="e.g., 2024"
        min={1888}
        max={2031}
      />

      <Input
        label="Date Rated"
        type="date"
        value={ratedAt}
        onChange={setRatedAt}
        max={getTodayString()}
      />

      <div className="form-group">
        <label className="form-label">Your Rating</label>
        <StarRating value={rating} onChange={setRating} size="lg" />
        {errors.rating && (
          <p className="form-error" role="alert">
            {errors.rating}
          </p>
        )}
      </div>

      <div className="mode-switch">
        <button
          type="button"
          className="mode-switch-link"
          onClick={handleSwitchToSearch}
        >
          Search instead
        </button>
      </div>

      <div className="form-actions-row">
        <Button
          type="button"
          variant="secondary"
          onClick={onCancel}
          disabled={isSubmitting}
          fullWidth
        >
          Cancel
        </Button>
        <Button
          type="submit"
          variant="primary"
          loading={isSubmitting}
          fullWidth
        >
          Add Movie
        </Button>
      </div>
    </form>
  );
}
