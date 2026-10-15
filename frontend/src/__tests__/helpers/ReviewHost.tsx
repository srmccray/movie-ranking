import { useState } from 'react';
import { ImportReview } from '../../components/ImportReview';
import { SESSION_ID } from './importReview';
import type { MatchedMovieItem } from '../../types';

interface HostProps {
  initialMovies: MatchedMovieItem[];
  currentIndex?: number;
  onAdd?: (rating: number, ratedAt?: string) => Promise<void>;
  onSkip?: () => Promise<void>;
  onComplete?: () => void;
  onMovieUpdated?: (index: number, movie: MatchedMovieItem) => void;
}

/** Owns the movie list like ImportWizard does, applying onMovieUpdated to its state. */
export function ReviewHost({
  initialMovies,
  currentIndex = 0,
  onAdd = async () => {},
  onSkip = async () => {},
  onComplete = () => {},
  onMovieUpdated,
}: HostProps) {
  const [movies, setMovies] = useState(initialMovies);
  return (
    <ImportReview
      movies={movies}
      currentIndex={currentIndex}
      sessionId={SESSION_ID}
      onAdd={onAdd}
      onSkip={onSkip}
      onComplete={onComplete}
      onMovieUpdated={(index, updated) => {
        onMovieUpdated?.(index, updated);
        setMovies((prev) => prev.map((m, i) => (i === index ? updated : m)));
      }}
    />
  );
}
