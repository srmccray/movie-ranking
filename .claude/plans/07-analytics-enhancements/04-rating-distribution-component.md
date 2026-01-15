# Task 04: Create RatingDistributionChart Component

## Agent
`frontend-react-engineer`

## Objective
Create a React component that displays a horizontal bar chart showing the distribution of user ratings.

## Component Specification

### Props Interface
```typescript
interface RatingCount {
  rating: number;
  count: number;
}

interface RatingDistributionChartProps {
  distribution: RatingCount[];
  total: number;
  isLoading?: boolean;
  error?: string | null;
}
```

### Visual Design

```
┌─────────────────────────────────────────────────┐
│ Rating Distribution                             │
│ 159 movies rated                                │
├─────────────────────────────────────────────────┤
│ ★★★★★  ████████████████████████████  42 (26%)  │
│ ★★★★   ████████████████████████████████████ 58 │
│ ★★★    ████████████████████████████  41        │
│ ★★     ████████  12                             │
│ ★      ████  6                                  │
└─────────────────────────────────────────────────┘
```

### Display Logic

#### Bar Width Calculation
```typescript
// Bars should be relative to the maximum count
const maxCount = Math.max(...distribution.map(d => d.count), 1);
const barWidth = (count / maxCount) * 100; // percentage
```

#### Star Labels
```typescript
// Show filled stars for the rating value
const getStarLabel = (rating: number): string => {
  return '★'.repeat(rating);
};
```

## Implementation Details

### Files to Create/Modify
1. `frontend/src/components/RatingDistributionChart.tsx` - New component
2. `frontend/src/components/index.ts` - Export component
3. `frontend/src/index.css` - Add styles
4. `frontend/src/types/index.ts` - Add types
5. `frontend/src/api/client.ts` - Add getRatingDistribution method

### Type Definitions
```typescript
// types/index.ts
export interface RatingCount {
  rating: number;
  count: number;
}

export interface RatingDistributionResponse {
  distribution: RatingCount[];
  total: number;
}
```

### API Client Method
```typescript
// api/client.ts
async getRatingDistribution(): Promise<RatingDistributionResponse> {
  return this.request<RatingDistributionResponse>('/analytics/rating-distribution/');
}
```

### Component Structure
```typescript
export function RatingDistributionChart({
  distribution,
  total,
  isLoading = false,
  error = null,
}: RatingDistributionChartProps) {
  const maxCount = useMemo(() => {
    return Math.max(...distribution.map(d => d.count), 1);
  }, [distribution]);

  if (isLoading) {
    return (
      <div className="rating-dist-chart rating-dist-chart-loading">
        <div className="spinner" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rating-dist-chart rating-dist-chart-error">
        <span>{error}</span>
      </div>
    );
  }

  // Display from 5 stars to 1 star (top to bottom)
  const sortedDistribution = [...distribution].sort((a, b) => b.rating - a.rating);

  return (
    <div className="rating-dist-chart">
      <div className="rating-dist-header">
        <h3 className="rating-dist-title">Rating Distribution</h3>
        <span className="rating-dist-total">
          {total} movie{total !== 1 ? 's' : ''} rated
        </span>
      </div>

      <div className="rating-dist-bars">
        {sortedDistribution.map(({ rating, count }) => {
          const percentage = maxCount > 0 ? (count / maxCount) * 100 : 0;
          return (
            <div key={rating} className="rating-dist-row">
              <span className="rating-dist-stars" aria-label={`${rating} stars`}>
                {'★'.repeat(rating)}
              </span>
              <div className="rating-dist-bar-container">
                <div
                  className="rating-dist-bar"
                  style={{ width: `${percentage}%` }}
                  role="progressbar"
                  aria-valuenow={count}
                  aria-valuemin={0}
                  aria-valuemax={maxCount}
                />
              </div>
              <span className="rating-dist-count">{count}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

### CSS Styles
```css
/* Rating Distribution Chart */
.rating-dist-chart {
  background-color: var(--color-bg-primary);
  border: 1px solid var(--color-neutral-200);
  border-radius: var(--radius-xl);
  padding: var(--space-4);
}

.rating-dist-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: var(--space-4);
}

.rating-dist-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-neutral-700);
  margin: 0;
}

.rating-dist-total {
  font-size: 0.875rem;
  color: var(--color-neutral-500);
}

.rating-dist-bars {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.rating-dist-row {
  display: grid;
  grid-template-columns: 60px 1fr 40px;
  align-items: center;
  gap: var(--space-2);
}

.rating-dist-stars {
  color: var(--color-star-filled);
  font-size: 0.75rem;
  text-align: right;
  letter-spacing: -1px;
}

.rating-dist-bar-container {
  height: 20px;
  background-color: var(--color-neutral-100);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.rating-dist-bar {
  height: 100%;
  background-color: var(--color-primary-500);
  border-radius: var(--radius-sm);
  transition: width 0.3s ease;
  min-width: 2px; /* Show a sliver even for very small counts */
}

.rating-dist-count {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-neutral-700);
  text-align: right;
}

.rating-dist-chart-loading,
.rating-dist-chart-error {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}

.rating-dist-chart-error {
  color: var(--color-error);
}

/* Hover effect on bars */
.rating-dist-row:hover .rating-dist-bar {
  background-color: var(--color-primary-600);
}
```

## Accessibility Requirements
- Bars should use `role="progressbar"` with aria attributes
- Star labels should have aria-label describing the rating
- Color contrast must meet WCAG AA
- Chart should be readable without colors (counts are always visible)

## Testing Requirements

### Test Cases
1. Renders all 5 rating bars
2. Bars are sorted 5 stars to 1 star (top to bottom)
3. Bar widths are proportional to counts
4. Shows loading state when isLoading is true
5. Shows error state when error is provided
6. Handles all-zero distribution gracefully
7. Handles single-rating distribution (only one bar has count > 0)

## Acceptance Criteria
- [ ] Component renders 5 horizontal bars
- [ ] Bars are ordered from 5 stars (top) to 1 star (bottom)
- [ ] Bar widths are relative to maximum count
- [ ] Star labels use filled star character
- [ ] Counts display next to each bar
- [ ] Header shows total count
- [ ] Loading and error states work
- [ ] Matches existing card styling
- [ ] Exported from components/index.ts
- [ ] ARIA attributes for accessibility
