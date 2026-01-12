interface AddMovieCardProps {
  onClick: () => void;
}

export function AddMovieCard({ onClick }: AddMovieCardProps) {
  return (
    <button
      type="button"
      className="add-movie-card"
      onClick={onClick}
      aria-label="Add a new movie to your rankings"
    >
      <div className="add-movie-card-icon" aria-hidden="true">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
      </div>
      <span className="add-movie-card-label">Add a movie</span>
      <span className="add-movie-card-hint">Search and rate</span>
    </button>
  );
}
