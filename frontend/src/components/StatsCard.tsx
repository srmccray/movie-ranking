interface StatsCardProps {
  totalMovies: number;
  topGenre: string | null;
  averageRating: number;
  currentStreak: number;
  isLoading: boolean;
  error: string | null;
}

/**
 * Format average rating with star symbol and 1 decimal place.
 * Example: "3.8" becomes "3.8 ★"
 */
function formatRating(rating: number): string {
  if (rating === 0) {
    return 'N/A';
  }
  return `${rating.toFixed(1)} ★`;
}

/**
 * Format streak with proper singular/plural handling.
 * Examples: "No streak", "1 day", "12 days"
 */
function formatStreak(days: number): string {
  if (days === 0) {
    return 'No streak';
  }
  return `${days} day${days !== 1 ? 's' : ''}`;
}

function LoadingSpinner() {
  return (
    <div className="stats-card-loading">
      <div className="spinner" />
    </div>
  );
}

function ErrorMessage({ message }: { message: string }) {
  return (
    <div className="stats-card-error" role="alert">
      <svg
        className="stats-card-error-icon"
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

interface StatItemProps {
  label: string;
  value: string;
  icon: React.ReactNode;
}

function StatItem({ label, value, icon }: StatItemProps) {
  return (
    <div className="stat-item">
      <div className="stat-item-icon">{icon}</div>
      <div className="stat-item-content">
        <span className="stat-item-value">{value}</span>
        <span className="stat-item-label">{label}</span>
      </div>
    </div>
  );
}

function FilmIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="2" y="2" width="20" height="20" rx="2" />
      <line x1="7" y1="2" x2="7" y2="22" />
      <line x1="17" y1="2" x2="17" y2="22" />
      <line x1="2" y1="12" x2="22" y2="12" />
      <line x1="2" y1="7" x2="7" y2="7" />
      <line x1="2" y1="17" x2="7" y2="17" />
      <line x1="17" y1="7" x2="22" y2="7" />
      <line x1="17" y1="17" x2="22" y2="17" />
    </svg>
  );
}

function TagIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z" />
      <line x1="7" y1="7" x2="7.01" y2="7" />
    </svg>
  );
}

function StarIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
    </svg>
  );
}

function FireIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M8.5 14.5A2.5 2.5 0 0011 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 11-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 002.5 2.5z" />
    </svg>
  );
}

export function StatsCard({
  totalMovies,
  topGenre,
  averageRating,
  currentStreak,
  isLoading,
  error,
}: StatsCardProps) {
  if (isLoading) {
    return (
      <div className="stats-card">
        <LoadingSpinner />
      </div>
    );
  }

  if (error) {
    return (
      <div className="stats-card">
        <ErrorMessage message={error} />
      </div>
    );
  }

  return (
    <div className="stats-card">
      <div className="stats-grid">
        <StatItem
          label="Total Movies"
          value={totalMovies.toLocaleString()}
          icon={<FilmIcon />}
        />
        <StatItem
          label="Top Genre"
          value={topGenre ?? 'No ratings'}
          icon={<TagIcon />}
        />
        <StatItem
          label="Avg Rating"
          value={formatRating(averageRating)}
          icon={<StarIcon />}
        />
        <StatItem
          label="Current Streak"
          value={formatStreak(currentStreak)}
          icon={<FireIcon />}
        />
      </div>
    </div>
  );
}
