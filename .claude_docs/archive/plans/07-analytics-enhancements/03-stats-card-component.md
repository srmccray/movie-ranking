# Task 03: Create StatsCard Component

## Agent
`frontend-react-engineer`

## Objective
Create a React component that displays key user statistics in a compact card format.

## Component Specification

### Props Interface
```typescript
interface StatsCardProps {
  totalMovies: number;
  totalWatchTimeMinutes: number;
  averageRating: number;
  currentStreak: number;
  isLoading?: boolean;
  error?: string | null;
}
```

### Visual Design

```
┌─────────────────────────────────────┐
│ Your Stats                          │
├──────────────┬──────────────────────┤
│     247      │      127 hrs         │
│   Movies     │    Watch Time        │
├──────────────┼──────────────────────┤
│    3.8 ★     │    12 day streak     │
│  Avg Rating  │   Current Streak     │
└──────────────┴──────────────────────┘
```

### Display Logic

#### Watch Time Formatting
```typescript
function formatWatchTime(minutes: number): string {
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (mins === 0) return `${hours} hrs`;
  return `${hours}h ${mins}m`;
}
// Examples:
// 45 -> "45 min"
// 120 -> "2 hrs"
// 7620 -> "127 hrs"
// 135 -> "2h 15m"
```

#### Streak Display
```typescript
// Show flame emoji for active streaks
// "12 day streak" or "No streak" if 0
```

#### Average Rating
```typescript
// Round to 1 decimal place
// Display with star: "3.8 ★"
```

## Implementation Details

### Files to Create/Modify
1. `frontend/src/components/StatsCard.tsx` - New component
2. `frontend/src/components/index.ts` - Export component
3. `frontend/src/index.css` - Add styles
4. `frontend/src/types/index.ts` - Add StatsResponse type
5. `frontend/src/api/client.ts` - Add getStats method

### Type Definitions
```typescript
// types/index.ts
export interface StatsResponse {
  total_movies: number;
  total_watch_time_minutes: number;
  average_rating: number;
  current_streak: number;
  longest_streak: number;
}
```

### API Client Method
```typescript
// api/client.ts
async getStats(): Promise<StatsResponse> {
  return this.request<StatsResponse>('/analytics/stats/');
}
```

### Component Structure
```typescript
export function StatsCard({
  totalMovies,
  totalWatchTimeMinutes,
  averageRating,
  currentStreak,
  isLoading = false,
  error = null,
}: StatsCardProps) {
  if (isLoading) {
    return (
      <div className="stats-card stats-card-loading">
        <div className="spinner" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="stats-card stats-card-error">
        <span>{error}</span>
      </div>
    );
  }

  return (
    <div className="stats-card">
      <h3 className="stats-card-title">Your Stats</h3>
      <div className="stats-card-grid">
        <div className="stats-card-item">
          <span className="stats-card-value">{totalMovies.toLocaleString()}</span>
          <span className="stats-card-label">Movies</span>
        </div>
        <div className="stats-card-item">
          <span className="stats-card-value">{formatWatchTime(totalWatchTimeMinutes)}</span>
          <span className="stats-card-label">Watch Time</span>
        </div>
        <div className="stats-card-item">
          <span className="stats-card-value">{averageRating.toFixed(1)} ★</span>
          <span className="stats-card-label">Avg Rating</span>
        </div>
        <div className="stats-card-item">
          <span className="stats-card-value">
            {currentStreak > 0 ? `${currentStreak} day${currentStreak !== 1 ? 's' : ''}` : 'No streak'}
          </span>
          <span className="stats-card-label">Current Streak</span>
        </div>
      </div>
    </div>
  );
}
```

### CSS Styles
```css
/* Stats Card */
.stats-card {
  background-color: var(--color-bg-primary);
  border: 1px solid var(--color-neutral-200);
  border-radius: var(--radius-xl);
  padding: var(--space-4);
}

.stats-card-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-neutral-700);
  margin-bottom: var(--space-3);
}

.stats-card-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
}

.stats-card-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.stats-card-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-neutral-900);
  line-height: 1.2;
}

.stats-card-label {
  font-size: 0.75rem;
  color: var(--color-neutral-500);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-top: var(--space-1);
}

.stats-card-loading,
.stats-card-error {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 180px;
}

.stats-card-error {
  color: var(--color-error);
}
```

## Accessibility Requirements
- Card should have appropriate heading hierarchy (h3)
- Values should be readable by screen readers
- Color contrast must meet WCAG AA (already using design tokens)

## Testing Requirements

### Test Cases
1. Renders all 4 metrics correctly
2. Formats watch time appropriately for different values
3. Shows loading state when isLoading is true
4. Shows error state when error is provided
5. Handles zero values gracefully
6. Handles large numbers (toLocaleString formatting)

## Acceptance Criteria
- [ ] Component renders 4 metrics in 2x2 grid
- [ ] Watch time is human-readable (hours, not just minutes)
- [ ] Average rating shows 1 decimal place with star
- [ ] Streak shows "No streak" when 0
- [ ] Loading spinner displays when loading
- [ ] Error message displays on error
- [ ] Matches existing card styling (border-radius, shadows)
- [ ] Exported from components/index.ts
