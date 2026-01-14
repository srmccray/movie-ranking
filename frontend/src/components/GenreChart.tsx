import { useMemo } from 'react';
import type { GenreStats } from '../types';

interface GenreChartProps {
  genres: GenreStats[];
  totalMovies: number;
}

const MAX_GENRES = 6;
const SIZE = 280;
const CENTER = SIZE / 2;
const RADIUS = 100;

// Default genres to fill the radar chart when user has fewer than 6
const DEFAULT_GENRES: { genre_id: number; genre_name: string }[] = [
  { genre_id: 28, genre_name: 'Action' },
  { genre_id: 35, genre_name: 'Comedy' },
  { genre_id: 18, genre_name: 'Drama' },
  { genre_id: 27, genre_name: 'Horror' },
  { genre_id: 10749, genre_name: 'Romance' },
  { genre_id: 878, genre_name: 'Sci-Fi' },
];

function polarToCartesian(angle: number, radius: number): { x: number; y: number } {
  // Start from top (-90 degrees) and go clockwise
  const radians = ((angle - 90) * Math.PI) / 180;
  return {
    x: CENTER + radius * Math.cos(radians),
    y: CENTER + radius * Math.sin(radians),
  };
}

function createPolygonPoints(values: number[], maxValue: number): string {
  const angleStep = 360 / values.length;
  return values
    .map((value, i) => {
      const normalizedRadius = (value / maxValue) * RADIUS;
      const { x, y } = polarToCartesian(i * angleStep, normalizedRadius);
      return `${x},${y}`;
    })
    .join(' ');
}

function createGridPolygon(level: number, sides: number): string {
  const angleStep = 360 / sides;
  const radius = (level / 3) * RADIUS;
  return Array.from({ length: sides })
    .map((_, i) => {
      const { x, y } = polarToCartesian(i * angleStep, radius);
      return `${x},${y}`;
    })
    .join(' ');
}

export function GenreChart({ genres, totalMovies }: GenreChartProps) {
  // Fill with placeholder genres if fewer than 6
  const topGenres = useMemo(() => {
    const userGenres = genres.slice(0, MAX_GENRES);
    if (userGenres.length >= MAX_GENRES) {
      return userGenres;
    }

    // Get genre IDs the user already has
    const existingIds = new Set(userGenres.map(g => g.genre_id));

    // Fill remaining slots with default genres (that user doesn't have)
    const filledGenres = [...userGenres];
    for (const defaultGenre of DEFAULT_GENRES) {
      if (filledGenres.length >= MAX_GENRES) break;
      if (!existingIds.has(defaultGenre.genre_id)) {
        filledGenres.push({
          ...defaultGenre,
          count: 0,
          average_rating: 0,
        });
      }
    }

    return filledGenres;
  }, [genres]);

  const maxCount = useMemo(() => {
    const counts = topGenres.map((g) => g.count).filter(c => c > 0);
    return Math.max(...counts, 1);
  }, [topGenres]);


  const sides = topGenres.length;
  const angleStep = 360 / sides;
  const dataPoints = createPolygonPoints(
    topGenres.map((g) => g.count),
    maxCount
  );

  return (
    <div className="genre-chart">
      <div className="genre-chart-header">
        <h3 className="genre-chart-title">Genre Distribution</h3>
        <span className="genre-chart-total">
          {totalMovies} movie{totalMovies !== 1 ? 's' : ''} rated
        </span>
      </div>

      <div className="genre-radar-container">
        <svg
          viewBox={`0 0 ${SIZE} ${SIZE}`}
          className="genre-radar"
          role="img"
          aria-label="Radar chart showing genre distribution"
        >
          {/* Grid circles */}
          {[1, 2, 3].map((level) => (
            <polygon
              key={level}
              points={createGridPolygon(level, sides)}
              className="genre-radar-grid"
            />
          ))}

          {/* Axis lines */}
          {topGenres.map((_, i) => {
            const { x, y } = polarToCartesian(i * angleStep, RADIUS);
            return (
              <line
                key={i}
                x1={CENTER}
                y1={CENTER}
                x2={x}
                y2={y}
                className="genre-radar-axis"
              />
            );
          })}

          {/* Data polygon */}
          <polygon
            points={dataPoints}
            className="genre-radar-data"
          />

          {/* Data points */}
          {topGenres.map((genre, i) => {
            const normalizedRadius = (genre.count / maxCount) * RADIUS;
            const { x, y } = polarToCartesian(i * angleStep, normalizedRadius);
            return (
              <circle
                key={genre.genre_id}
                cx={x}
                cy={y}
                r={4}
                className="genre-radar-point"
              />
            );
          })}
        </svg>

        {/* Labels positioned around the chart */}
        <div className="genre-radar-labels">
          {topGenres.map((genre, i) => {
            const { x, y } = polarToCartesian(i * angleStep, RADIUS + 35);
            return (
              <div
                key={genre.genre_id}
                className={`genre-radar-label ${genre.count === 0 ? 'genre-radar-label-empty' : ''}`}
                style={{
                  left: `${(x / SIZE) * 100}%`,
                  top: `${(y / SIZE) * 100}%`,
                }}
              >
                <span className="genre-radar-label-name">{genre.genre_name}</span>
                {genre.count > 0 && (
                  <span className="genre-radar-label-count">{genre.count}</span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
