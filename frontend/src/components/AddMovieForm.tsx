import { useState } from 'react';
import { Input } from './Input';
import { Button } from './Button';
import { StarRating } from './StarRating';
import type { MovieCreate } from '../types';

interface AddMovieFormProps {
  onSubmit: (movie: MovieCreate, rating: number, ratedAt?: string) => Promise<void>;
  onCancel: () => void;
}

interface FormErrors {
  title?: string;
  year?: string;
  rating?: string;
}

function getTodayString(): string {
  return new Date().toISOString().split('T')[0];
}

export function AddMovieForm({ onSubmit, onCancel }: AddMovieFormProps) {
  const [title, setTitle] = useState('');
  const [year, setYear] = useState('');
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
      };

      await onSubmit(movieData, rating, ratedAt);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to add movie');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
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

      <div style={{ display: 'flex', gap: 'var(--space-3)', marginTop: 'var(--space-6)' }}>
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
