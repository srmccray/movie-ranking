# Task 05: Update Analytics Page Layout

## Agent
`frontend-react-engineer`

## Objective
Update the AnalyticsPage component to use a 2x2 grid layout with all four analytics cards.

## Layout Specification

### Desktop Layout (>1024px)
```
┌────────────────────────────────────┬──────────────────┐
│                                    │                  │
│         Activity Chart             │    Stats Card    │
│            (65%)                   │      (35%)       │
│                                    │                  │
├──────────────────┬─────────────────┴──────────────────┤
│                  │                                    │
│   Genre Chart    │    Rating Distribution Chart       │
│      (50%)       │            (50%)                   │
│                  │                                    │
└──────────────────┴────────────────────────────────────┘
```

### Tablet Layout (768px - 1024px)
```
┌─────────────────────────────────────────────────────┐
│                Activity Chart                        │
├─────────────────────────────────────────────────────┤
│                  Stats Card                          │
├─────────────────────────────────────────────────────┤
│                  Genre Chart                         │
├─────────────────────────────────────────────────────┤
│           Rating Distribution Chart                  │
└─────────────────────────────────────────────────────┘
```

### Mobile Layout (<768px)
Same as tablet - full width stacked cards

## Implementation Details

### Files to Modify
1. `frontend/src/pages/AnalyticsPage.tsx` - Update layout and data fetching
2. `frontend/src/index.css` - Add new grid styles

### Updated AnalyticsPage Component

```typescript
import { useEffect, useState, useCallback } from 'react';
import { Header } from '../components/Header';
import { ActivityChart } from '../components/ActivityChart';
import { GenreChart } from '../components/GenreChart';
import { StatsCard } from '../components/StatsCard';
import { RatingDistributionChart } from '../components/RatingDistributionChart';
import { Button } from '../components/Button';
import { apiClient, ApiClientError } from '../api/client';
import type {
  ActivityResponse,
  GenreResponse,
  StatsResponse,
  RatingDistributionResponse,
} from '../types';

interface AnalyticsData {
  activity: ActivityResponse | null;
  genres: GenreResponse | null;
  stats: StatsResponse | null;
  ratingDistribution: RatingDistributionResponse | null;
}

interface LoadingState {
  activity: boolean;
  genres: boolean;
  stats: boolean;
  ratingDistribution: boolean;
}

interface ErrorState {
  activity: string | null;
  genres: string | null;
  stats: string | null;
  ratingDistribution: string | null;
}

export function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsData>({
    activity: null,
    genres: null,
    stats: null,
    ratingDistribution: null,
  });

  const [loading, setLoading] = useState<LoadingState>({
    activity: true,
    genres: true,
    stats: true,
    ratingDistribution: true,
  });

  const [errors, setErrors] = useState<ErrorState>({
    activity: null,
    genres: null,
    stats: null,
    ratingDistribution: null,
  });

  const fetchAllData = useCallback(async () => {
    // Reset all loading states
    setLoading({
      activity: true,
      genres: true,
      stats: true,
      ratingDistribution: true,
    });
    setErrors({
      activity: null,
      genres: null,
      stats: null,
      ratingDistribution: null,
    });

    // Fetch all data in parallel
    const results = await Promise.allSettled([
      apiClient.getActivity(),
      apiClient.getGenres(),
      apiClient.getStats(),
      apiClient.getRatingDistribution(),
    ]);

    // Process activity result
    if (results[0].status === 'fulfilled') {
      setData(prev => ({ ...prev, activity: results[0].value }));
    } else {
      setErrors(prev => ({
        ...prev,
        activity: results[0].reason?.message || 'Failed to load activity',
      }));
    }
    setLoading(prev => ({ ...prev, activity: false }));

    // Process genres result
    if (results[1].status === 'fulfilled') {
      setData(prev => ({ ...prev, genres: results[1].value }));
    } else {
      setErrors(prev => ({
        ...prev,
        genres: results[1].reason?.message || 'Failed to load genres',
      }));
    }
    setLoading(prev => ({ ...prev, genres: false }));

    // Process stats result
    if (results[2].status === 'fulfilled') {
      setData(prev => ({ ...prev, stats: results[2].value }));
    } else {
      setErrors(prev => ({
        ...prev,
        stats: results[2].reason?.message || 'Failed to load stats',
      }));
    }
    setLoading(prev => ({ ...prev, stats: false }));

    // Process rating distribution result
    if (results[3].status === 'fulfilled') {
      setData(prev => ({ ...prev, ratingDistribution: results[3].value }));
    } else {
      setErrors(prev => ({
        ...prev,
        ratingDistribution: results[3].reason?.message || 'Failed to load rating distribution',
      }));
    }
    setLoading(prev => ({ ...prev, ratingDistribution: false }));
  }, []);

  useEffect(() => {
    fetchAllData();
  }, [fetchAllData]);

  const isAnyLoading = Object.values(loading).some(Boolean);
  const hasAnyError = Object.values(errors).some(Boolean);

  return (
    <>
      <Header />
      <main className="main-layout">
        <div className="container">
          <div className="page-content">
            <div className="page-header">
              <h1 className="page-title">Analytics</h1>
            </div>

            {/* Global error retry */}
            {hasAnyError && !isAnyLoading && (
              <div className="alert alert-error" role="alert">
                Some data failed to load.
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={fetchAllData}
                  style={{ marginLeft: 'var(--space-2)' }}
                >
                  Retry All
                </Button>
              </div>
            )}

            <div className="analytics-dashboard">
              {/* Row 1: Activity Chart + Stats Card */}
              <div className="analytics-row analytics-row-1">
                <div className="analytics-card analytics-card-wide">
                  {data.activity ? (
                    <ActivityChart
                      activity={data.activity.activity}
                      startDate={data.activity.start_date}
                      endDate={data.activity.end_date}
                    />
                  ) : loading.activity ? (
                    <div className="analytics-placeholder">
                      <div className="spinner" />
                    </div>
                  ) : errors.activity ? (
                    <div className="analytics-placeholder analytics-error">
                      {errors.activity}
                    </div>
                  ) : null}
                </div>

                <div className="analytics-card analytics-card-narrow">
                  <StatsCard
                    totalMovies={data.stats?.total_movies ?? 0}
                    totalWatchTimeMinutes={data.stats?.total_watch_time_minutes ?? 0}
                    averageRating={data.stats?.average_rating ?? 0}
                    currentStreak={data.stats?.current_streak ?? 0}
                    isLoading={loading.stats}
                    error={errors.stats}
                  />
                </div>
              </div>

              {/* Row 2: Genre Chart + Rating Distribution */}
              <div className="analytics-row analytics-row-2">
                <div className="analytics-card analytics-card-half">
                  {data.genres ? (
                    <GenreChart
                      genres={data.genres.genres}
                      totalMovies={data.genres.total_movies}
                    />
                  ) : loading.genres ? (
                    <div className="analytics-placeholder">
                      <div className="spinner" />
                    </div>
                  ) : errors.genres ? (
                    <div className="analytics-placeholder analytics-error">
                      {errors.genres}
                    </div>
                  ) : null}
                </div>

                <div className="analytics-card analytics-card-half">
                  <RatingDistributionChart
                    distribution={data.ratingDistribution?.distribution ?? []}
                    total={data.ratingDistribution?.total ?? 0}
                    isLoading={loading.ratingDistribution}
                    error={errors.ratingDistribution}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
```

### CSS Styles

```css
/* Analytics Dashboard Grid */
.analytics-dashboard {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.analytics-row {
  display: grid;
  gap: var(--space-4);
}

/* Row 1: 65% / 35% split */
.analytics-row-1 {
  grid-template-columns: 1fr;
}

@media (min-width: 1024px) {
  .analytics-row-1 {
    grid-template-columns: 65fr 35fr;
  }
}

/* Row 2: 50% / 50% split */
.analytics-row-2 {
  grid-template-columns: 1fr;
}

@media (min-width: 1024px) {
  .analytics-row-2 {
    grid-template-columns: 1fr 1fr;
  }
}

/* Card containers */
.analytics-card {
  min-height: 200px;
}

/* Placeholder for loading/error states */
.analytics-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  background-color: var(--color-bg-primary);
  border: 1px solid var(--color-neutral-200);
  border-radius: var(--radius-xl);
}

.analytics-placeholder.analytics-error {
  color: var(--color-error);
  padding: var(--space-4);
  text-align: center;
}

/* Remove old analytics-grid styles if they exist */
.analytics-grid {
  display: none; /* Deprecated - use analytics-dashboard */
}
```

## Data Fetching Strategy

### Parallel Fetching
All four API calls should be made in parallel using `Promise.allSettled`:
- Each card has independent loading/error state
- One failing endpoint doesn't block others
- "Retry All" button refreshes everything

### Individual Card States
Each card handles its own:
- Loading spinner
- Error message
- Empty state

## Testing Requirements

### Test Cases
1. All 4 cards render in correct grid positions
2. Desktop layout shows 2 rows with correct proportions
3. Mobile layout stacks all cards vertically
4. Individual card errors don't affect other cards
5. Loading states appear for each card independently
6. "Retry All" button refetches all data

## Acceptance Criteria
- [ ] 2x2 grid layout on desktop (>1024px)
- [ ] Row 1 is 65%/35% split
- [ ] Row 2 is 50%/50% split
- [ ] Mobile/tablet stacks cards vertically
- [ ] Each card has independent loading/error handling
- [ ] Global "Retry All" button when any error occurs
- [ ] All 4 API calls made in parallel
- [ ] Smooth transitions between states
- [ ] Maintains existing Header and page structure
