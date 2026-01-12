import { useState } from 'react';
import { StarRating } from './StarRating';
import type { RankingWithMovie } from '../types';

interface MovieCardProps {
  ranking: RankingWithMovie;
  onRatingChange?: (movieId: string, rating: number) => void;
  onDelete?: (rankingId: string) => void;
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export function MovieCard({ ranking, onRatingChange, onDelete }: MovieCardProps) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const { movie, rating, rated_at } = ranking;

  const handleRatingChange = (newRating: number) => {
    if (onRatingChange) {
      onRatingChange(movie.id, newRating);
    }
  };

  const handleDeleteClick = () => {
    setShowDeleteConfirm(true);
  };

  const handleConfirmDelete = () => {
    if (onDelete) {
      onDelete(ranking.id);
    }
    setShowDeleteConfirm(false);
  };

  const handleCancelDelete = () => {
    setShowDeleteConfirm(false);
  };

  return (
    <article className="card movie-card">
      <div className="movie-poster">
        {movie.poster_url ? (
          <img
            src={movie.poster_url}
            alt={`${movie.title} poster`}
            className="movie-poster-image"
            loading="lazy"
          />
        ) : (
          <div className="movie-poster-placeholder" aria-label="No poster available">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <rect x="2" y="2" width="20" height="20" rx="2" />
              <circle cx="8" cy="8" r="2" />
              <path d="M21 15l-5-5L5 21" />
            </svg>
          </div>
        )}
      </div>
      <div className="movie-info">
        <h3 className="movie-title">{movie.title}</h3>
        {movie.year && <p className="movie-year">{movie.year}</p>}
        <p className="movie-date">Rated {formatDate(rated_at)}</p>
      </div>
      <div className="movie-actions">
        <div className="movie-rating">
          <StarRating
            value={rating}
            onChange={onRatingChange ? handleRatingChange : undefined}
            readonly={!onRatingChange}
            size="md"
          />
        </div>
        {onDelete && (
          <button
            className="btn-icon btn-delete"
            onClick={handleDeleteClick}
            aria-label={`Delete ${movie.title}`}
            title="Delete ranking"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
            </svg>
          </button>
        )}
      </div>

      {showDeleteConfirm && (
        <div className="delete-confirm">
          <p>Delete ranking for "{movie.title}"?</p>
          <div className="delete-confirm-actions">
            <button className="btn btn-secondary btn-sm" onClick={handleCancelDelete}>
              Cancel
            </button>
            <button className="btn btn-danger btn-sm" onClick={handleConfirmDelete}>
              Delete
            </button>
          </div>
        </div>
      )}
    </article>
  );
}
