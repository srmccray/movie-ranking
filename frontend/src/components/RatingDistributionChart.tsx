import { useMemo } from 'react';
import type { RatingCount } from '../types';

interface RatingDistributionChartProps {
  distribution: RatingCount[];
  total: number;
  isLoading?: boolean;
  error?: string | null;
}

function LoadingSpinner() {
  return (
    <div className="rating-distribution-loading">
      <div className="spinner" />
    </div>
  );
}

function ErrorMessage({ message }: { message: string }) {
  return (
    <div className="rating-distribution-error" role="alert">
      <svg
        className="rating-distribution-error-icon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
      >
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>
      <span>{message}</span>
    </div>
  );
}

interface RatingBarProps {
  rating: number;
  count: number;
  maxCount: number;
}

function RatingBar({ rating, count, maxCount }: RatingBarProps) {
  const percentage = maxCount > 0 ? (count / maxCount) * 100 : 0;
  const stars = '\u2605'.repeat(rating);

  return (
    <div className="rating-bar-row">
      <span
        className="rating-bar-label"
        aria-label={`${rating} star${rating !== 1 ? 's' : ''}`}
      >
        {stars}
      </span>
      <div className="rating-bar-track">
        <div
          className="rating-bar-fill"
          style={{ width: `${percentage}%` }}
          role="progressbar"
          aria-valuenow={count}
          aria-valuemin={0}
          aria-valuemax={maxCount}
          aria-label={`${count} movie${count !== 1 ? 's' : ''} rated ${rating} star${rating !== 1 ? 's' : ''}`}
        />
      </div>
      <span className="rating-bar-count">{count}</span>
    </div>
  );
}

export function RatingDistributionChart({
  distribution,
  total,
  isLoading = false,
  error = null,
}: RatingDistributionChartProps) {
  // Build a map of rating to count for easy lookup
  const ratingMap = useMemo(() => {
    const map = new Map<number, number>();
    for (const item of distribution) {
      map.set(item.rating, item.count);
    }
    return map;
  }, [distribution]);

  // Get the maximum count for scaling bars
  const maxCount = useMemo(() => {
    if (distribution.length === 0) return 0;
    return Math.max(...distribution.map((item) => item.count));
  }, [distribution]);

  // Ratings ordered from 5 to 1 (top to bottom)
  const ratings = [5, 4, 3, 2, 1];

  if (isLoading) {
    return (
      <div className="rating-distribution-chart">
        <LoadingSpinner />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rating-distribution-chart">
        <ErrorMessage message={error} />
      </div>
    );
  }

  return (
    <div className="rating-distribution-chart">
      <div className="rating-distribution-header">
        <h3 className="rating-distribution-title">Rating Distribution</h3>
        <span className="rating-distribution-total">
          {total} movie{total !== 1 ? 's' : ''} rated
        </span>
      </div>

      <div className="rating-distribution-bars">
        {ratings.map((rating) => (
          <RatingBar
            key={rating}
            rating={rating}
            count={ratingMap.get(rating) ?? 0}
            maxCount={maxCount}
          />
        ))}
      </div>
    </div>
  );
}
