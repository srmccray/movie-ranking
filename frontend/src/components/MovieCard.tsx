import { StarRating } from './StarRating';
import type { RankingWithMovie } from '../types';

interface MovieCardProps {
  ranking: RankingWithMovie;
  onRatingChange?: (movieId: string, rating: number) => void;
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export function MovieCard({ ranking, onRatingChange }: MovieCardProps) {
  const { movie, rating, updated_at } = ranking;

  const handleRatingChange = (newRating: number) => {
    if (onRatingChange) {
      onRatingChange(movie.id, newRating);
    }
  };

  return (
    <article className="card movie-card">
      <div className="movie-info">
        <h3 className="movie-title">{movie.title}</h3>
        {movie.year && <p className="movie-year">{movie.year}</p>}
        <p className="movie-date">Rated {formatDate(updated_at)}</p>
      </div>
      <div className="movie-rating">
        <StarRating
          value={rating}
          onChange={onRatingChange ? handleRatingChange : undefined}
          readonly={!onRatingChange}
          size="md"
        />
      </div>
    </article>
  );
}
