import { useState, useRef, useEffect } from 'react';
import { StarRating } from './StarRating';
import type { RankingWithMovie } from '../types';

interface MovieCardProps {
  ranking: RankingWithMovie;
  onRatingChange?: (movieId: string, rating: number) => void;
  onRatedAtChange?: (rankingId: string, movieId: string, ratedAt: string) => Promise<void>;
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

function toInputDateValue(isoString: string): string {
  return isoString.split('T')[0];
}

function getTodayString(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function MovieCard({ ranking, onRatingChange, onRatedAtChange, onDelete }: MovieCardProps) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isEditingDate, setIsEditingDate] = useState(false);
  const [editedDate, setEditedDate] = useState('');
  const [isSavingDate, setIsSavingDate] = useState(false);

  const editButtonRef = useRef<HTMLButtonElement>(null);
  const dateInputRef = useRef<HTMLInputElement>(null);

  const { movie, rating, rated_at } = ranking;

  const handleStartEditDate = () => {
    setEditedDate(toInputDateValue(rated_at));
    setIsEditingDate(true);
  };

  useEffect(() => {
    if (isEditingDate && dateInputRef.current) {
      dateInputRef.current.focus();
    }
  }, [isEditingDate]);

  const handleCancelEditDate = () => {
    setIsEditingDate(false);
    setEditedDate('');
    editButtonRef.current?.focus();
  };

  const handleSaveDate = async () => {
    if (!onRatedAtChange || !editedDate) return;

    setIsSavingDate(true);
    try {
      // Append T00:00:00Z to interpret the date as midnight UTC, not local time
      const isoDate = new Date(editedDate + 'T00:00:00Z').toISOString();
      await onRatedAtChange(ranking.id, movie.id, isoDate);
      setIsEditingDate(false);
      editButtonRef.current?.focus();
    } catch (error) {
      console.error('Failed to update date:', error);
    } finally {
      setIsSavingDate(false);
    }
  };

  const handleDateKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSaveDate();
    } else if (e.key === 'Escape') {
      handleCancelEditDate();
    }
  };

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

        {isEditingDate && onRatedAtChange ? (
          <div className={`movie-date-editor ${isSavingDate ? 'saving' : ''}`}>
            <input
              ref={dateInputRef}
              type="date"
              className="movie-date-input"
              value={editedDate}
              onChange={(e) => setEditedDate(e.target.value)}
              onKeyDown={handleDateKeyDown}
              max={getTodayString()}
              aria-label="Rated date"
              disabled={isSavingDate}
            />
            <div className="movie-date-actions">
              <button
                className="btn-icon-sm btn-icon-save"
                onClick={handleSaveDate}
                aria-label="Save date"
                disabled={isSavingDate}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </button>
              <button
                className="btn-icon-sm btn-icon-cancel"
                onClick={handleCancelEditDate}
                aria-label="Cancel"
                disabled={isSavingDate}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
          </div>
        ) : onRatedAtChange ? (
          <button
            ref={editButtonRef}
            className="movie-date-edit"
            onClick={handleStartEditDate}
            aria-label={`Edit rated date for ${movie.title}, currently ${formatDate(rated_at)}`}
          >
            <span>Rated {formatDate(rated_at)}</span>
            <svg className="movie-date-edit-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z" />
            </svg>
          </button>
        ) : (
          <p className="movie-date">Rated {formatDate(rated_at)}</p>
        )}
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
