# Task 01: Create Stats Summary Endpoint

## Agent
`backend-engineer`

## Objective
Create a new API endpoint that returns user statistics for the analytics dashboard.

## Endpoint Specification

### Route
```
GET /api/v1/analytics/stats/
```

### Response Schema
```python
class StatsResponse(BaseModel):
    """Schema for user stats response.

    RESPONSE SHAPE: { total_movies, total_watch_time_minutes, average_rating, current_streak, longest_streak }
    """
    total_movies: int = Field(..., ge=0, description="Total movies rated by user")
    total_watch_time_minutes: int = Field(..., ge=0, description="Total runtime of all rated movies in minutes")
    average_rating: float = Field(..., ge=0, le=5, description="Average rating across all movies")
    current_streak: int = Field(..., ge=0, description="Current consecutive days with ratings")
    longest_streak: int = Field(..., ge=0, description="Longest consecutive days streak ever")
```

### Response Example
```json
{
  "total_movies": 247,
  "total_watch_time_minutes": 7620,
  "average_rating": 3.8,
  "current_streak": 12,
  "longest_streak": 45
}
```

## Implementation Details

### Files to Create/Modify
1. `app/schemas/analytics.py` - Add `StatsResponse` schema
2. `app/routers/analytics.py` - Add `get_stats` endpoint

### Query Logic

#### Total Movies & Average Rating
```python
# Single query for total count and average
result = await db.execute(
    select(
        func.count(Ranking.id).label("total"),
        func.avg(Ranking.rating).label("avg_rating"),
    )
    .where(Ranking.user_id == current_user.id)
)
```

#### Total Watch Time
```python
# Join with movies to sum runtime
result = await db.execute(
    select(func.sum(Movie.runtime))
    .select_from(Ranking)
    .join(Movie, Ranking.movie_id == Movie.id)
    .where(Ranking.user_id == current_user.id)
)
```

#### Streak Calculation
```python
def calculate_streaks(rating_dates: list[date]) -> tuple[int, int]:
    """Calculate current and longest streaks from sorted rating dates.

    A streak is consecutive days where the user rated at least one movie.
    Current streak counts back from today (or yesterday if no rating today).

    Args:
        rating_dates: List of unique dates with ratings, sorted ascending

    Returns:
        Tuple of (current_streak, longest_streak)
    """
    if not rating_dates:
        return 0, 0

    today = date.today()
    unique_dates = sorted(set(rating_dates))

    # Calculate longest streak
    longest = 1
    current_run = 1
    for i in range(1, len(unique_dates)):
        if (unique_dates[i] - unique_dates[i-1]).days == 1:
            current_run += 1
            longest = max(longest, current_run)
        else:
            current_run = 1

    # Calculate current streak (must include today or yesterday)
    current = 0
    if unique_dates:
        last_date = unique_dates[-1]
        if last_date == today or last_date == today - timedelta(days=1):
            current = 1
            for i in range(len(unique_dates) - 2, -1, -1):
                if (unique_dates[i+1] - unique_dates[i]).days == 1:
                    current += 1
                else:
                    break

    return current, longest
```

### Edge Cases
- User with no ratings: Return zeros for all metrics
- Movies with null runtime: Exclude from watch time calculation
- Current streak: Include today AND yesterday as valid "current" (user might not have watched today yet)

## Testing Requirements

### Test Cases
1. `test_stats_empty_user` - New user with no ratings returns zeros
2. `test_stats_with_ratings` - User with ratings returns correct totals
3. `test_stats_streak_calculation` - Verify streak logic with known dates
4. `test_stats_average_rating` - Verify average calculation
5. `test_stats_watch_time_excludes_null_runtime` - Handle movies without runtime
6. `test_stats_requires_auth` - Returns 401 without token

## Acceptance Criteria
- [ ] Endpoint returns 200 with valid stats for authenticated user
- [ ] Endpoint returns 401 for unauthenticated requests
- [ ] All metrics are correctly calculated
- [ ] Streak calculation handles edge cases (gaps, today vs yesterday)
- [ ] Watch time handles null runtime gracefully
- [ ] Trailing slash on endpoint URL
- [ ] Schema documented with RESPONSE SHAPE comment
