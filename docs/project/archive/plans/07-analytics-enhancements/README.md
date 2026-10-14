# Feature: Analytics Dashboard Enhancements

## Overview

Enhance the analytics page with a 2-row, 4-card dashboard layout providing comprehensive movie watching insights.

## Current State

The analytics page (`/analytics`) currently displays:
1. **Activity Chart**: GitHub-style contribution grid showing movies rated per day (rolling 12 months)
2. **Genre Chart**: Radar chart showing top 6 genres by count

Both charts are displayed in a simple vertical stack layout.

## Target State

A professional 2x2 dashboard grid with:
- **Row 1**: Activity Chart (65% width) + Stats Summary Card (35% width)
- **Row 2**: Genre Chart (50% width) + Rating Distribution Chart (50% width)

## UX Research Summary

Based on research into leading movie tracking platforms (Letterboxd, Trakt, TV Time, IMDb), the following design decisions were made:

### Stats Summary Card
Display 4 key metrics that users find most valuable:
| Metric | Rationale |
|--------|-----------|
| **Total Movies Rated** | Core vanity metric; immediate engagement signal |
| **Total Watch Time** | High-impact "wow" number (e.g., "127 hours") |
| **Average Rating** | Shows user's rating tendencies |
| **Current Streak** | Gamification element; drives daily engagement |

### Rating Distribution Chart (4th Card)
A horizontal bar chart showing distribution of user ratings.

**Why this choice:**
- Highest user insight value - answers "What kind of critic am I?"
- Visual diversity - bar chart complements radar chart and heatmap
- Data already available - no new API calls needed
- Industry-proven - used by Letterboxd, IMDb, Amazon, etc.
- Instantly scannable - follows 5-second dashboard rule

### Layout Rationale
- **Asymmetric top row (65/35)**: Activity chart is the "hero" visualization; counts card is dense with numbers
- **Equal bottom row (50/50)**: Both are detailed visualizations requiring similar space
- **F-pattern reading**: Users naturally scan top-left to right, then down

## Technical Considerations

### Backend Changes
1. **New Analytics Endpoint**: `GET /api/v1/analytics/stats/`
   - Returns: total_movies, total_watch_time_minutes, average_rating, current_streak, longest_streak
   - Requires: JOIN with movies table for runtime data
   - Streak calculation: consecutive days with ratings

2. **New Analytics Endpoint**: `GET /api/v1/analytics/rating-distribution/`
   - Returns: array of { rating: number, count: number } for ratings 1-5
   - Simple GROUP BY query on rankings table

### Frontend Changes
1. **StatsCard Component**: Display 4 key metrics in 2x2 grid
2. **RatingDistributionChart Component**: Horizontal bar chart
3. **Layout Update**: CSS Grid for 2-row responsive layout
4. **Types**: New interfaces for stats and distribution responses

### Data Requirements
- Runtime data from TMDB (already stored in movies table as `runtime`)
- Streak calculation requires ordered date analysis
- All data is user-scoped (filter by user_id)

## Success Criteria

1. Dashboard renders 4 cards in 2x2 grid on desktop
2. Stats card shows accurate metrics (verified with test data)
3. Rating distribution accurately reflects user's ratings
4. Mobile view stacks cards vertically
5. Loading states for each card
6. All existing tests pass
7. New endpoint tests added

## Out of Scope

- Year filter/selector (rolling year is sufficient)
- Comparison with previous periods
- Director/actor analysis (future enhancement)
- Geographic/country breakdown (future enhancement)

## References

- [Letterboxd Year in Review](https://letterboxd.com/journal/2025-letterboxd-year-in-review-faq/)
- [Dashboard UX Best Practices](https://www.justinmind.com/ui-design/dashboard-design-best-practices-ux)
- Previous analytics implementation: `.claude/retros/2026-01-13-analytics-feature.md`
