import { useState, useMemo } from 'react';
import type { GenreStats } from '../types';

interface GenreChartProps {
  genres: GenreStats[];
  totalMovies: number;
}

const DEFAULT_VISIBLE = 8;

function getRatingClass(rating: number): string {
  if (rating >= 4) return 'rating-high';
  if (rating >= 2.5) return 'rating-medium';
  return 'rating-low';
}

export function GenreChart({ genres, totalMovies }: GenreChartProps) {
  const [showAll, setShowAll] = useState(false);

  const maxCount = useMemo(() => {
    return Math.max(...genres.map((g) => g.count), 1);
  }, [genres]);

  const visibleGenres = showAll ? genres : genres.slice(0, DEFAULT_VISIBLE);
  const hasMore = genres.length > DEFAULT_VISIBLE;

  if (genres.length === 0) {
    return (
      <div className="genre-chart">
        <div className="genre-chart-header">
          <h3 className="genre-chart-title">Genre Distribution</h3>
        </div>
        <div className="genre-chart-empty">
          <p className="genre-chart-empty-text">No genre data available</p>
          <p className="genre-chart-empty-hint">
            Rate more movies to see your genre preferences
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="genre-chart">
      <div className="genre-chart-header">
        <h3 className="genre-chart-title">Genre Distribution</h3>
        <span className="genre-chart-total">
          {totalMovies} movie{totalMovies !== 1 ? 's' : ''} across {genres.length} genre{genres.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div
        className="genre-chart-bars"
        role="list"
        aria-label="Genres ranked by movies rated"
      >
        {visibleGenres.map((genre) => {
          const widthPercent = (genre.count / maxCount) * 100;

          return (
            <div
              key={genre.genre_id}
              className="genre-bar-row"
              role="listitem"
              aria-label={`${genre.genre_name}: ${genre.count} movies, average rating ${genre.average_rating} out of 5 stars`}
              tabIndex={0}
            >
              <span className="genre-bar-label">{genre.genre_name}</span>
              <div className="genre-bar-track">
                <div
                  className="genre-bar-fill"
                  style={{ width: `${widthPercent}%` }}
                />
              </div>
              <span className="genre-bar-count">{genre.count}</span>
              <span className={`genre-bar-rating ${getRatingClass(genre.average_rating)}`}>
                {genre.average_rating.toFixed(1)}
              </span>
            </div>
          );
        })}
      </div>

      {hasMore && (
        <button
          className="genre-chart-toggle"
          onClick={() => setShowAll(!showAll)}
          aria-expanded={showAll}
        >
          {showAll ? 'Show less' : `Show all ${genres.length} genres`}
        </button>
      )}
    </div>
  );
}
