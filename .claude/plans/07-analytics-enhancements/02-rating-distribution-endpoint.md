# Task 02: Create Rating Distribution Endpoint

## Agent
`backend-engineer`

## Objective
Create a new API endpoint that returns the distribution of user ratings for the analytics dashboard.

## Endpoint Specification

### Route
```
GET /api/v1/analytics/rating-distribution/
```

### Response Schema
```python
class RatingCount(BaseModel):
    """Schema for a single rating count.

    Attributes:
        rating: The rating value (1-5).
        count: Number of movies with this rating.
    """
    rating: int = Field(..., ge=1, le=5, description="Rating value")
    count: int = Field(..., ge=0, description="Number of movies with this rating")


class RatingDistributionResponse(BaseModel):
    """Schema for rating distribution response.

    RESPONSE SHAPE: { distribution: [...], total: N }

    Returns counts for all rating values 1-5, even if count is 0.
    """
    distribution: list[RatingCount] = Field(
        ..., description="Count of movies for each rating 1-5"
    )
    total: int = Field(..., ge=0, description="Total number of rated movies")
```

### Response Example
```json
{
  "distribution": [
    { "rating": 1, "count": 6 },
    { "rating": 2, "count": 12 },
    { "rating": 3, "count": 41 },
    { "rating": 4, "count": 58 },
    { "rating": 5, "count": 42 }
  ],
  "total": 159
}
```

## Implementation Details

### Files to Create/Modify
1. `app/schemas/analytics.py` - Add `RatingCount` and `RatingDistributionResponse` schemas
2. `app/routers/analytics.py` - Add `get_rating_distribution` endpoint

### Query Logic

```python
@router.get(
    "/rating-distribution/",
    response_model=RatingDistributionResponse,
    summary="Get rating distribution",
    responses={
        200: {"description": "Rating distribution retrieved successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def get_rating_distribution(
    current_user: CurrentUser,
    db: DbSession,
) -> RatingDistributionResponse:
    """Get distribution of user ratings.

    Returns the count of movies for each rating value (1-5).
    All rating values are included, even if count is 0.

    Args:
        current_user: The authenticated user (from JWT token).
        db: Async database session.

    Returns:
        RatingDistributionResponse with distribution array and total.
    """
    # Query rating counts grouped by rating value
    result = await db.execute(
        select(
            Ranking.rating,
            func.count(Ranking.id).label("count"),
        )
        .where(Ranking.user_id == current_user.id)
        .group_by(Ranking.rating)
        .order_by(Ranking.rating)
    )
    rows = result.all()

    # Build distribution with all ratings 1-5 (fill missing with 0)
    counts_map = {row.rating: row.count for row in rows}
    distribution = [
        RatingCount(rating=r, count=counts_map.get(r, 0))
        for r in range(1, 6)
    ]

    total = sum(rc.count for rc in distribution)

    return RatingDistributionResponse(
        distribution=distribution,
        total=total,
    )
```

### Edge Cases
- User with no ratings: Return all zeros with total=0
- User who only uses certain ratings: Fill missing ratings with count=0

## Testing Requirements

### Test Cases
1. `test_rating_distribution_empty_user` - New user returns zeros for all ratings
2. `test_rating_distribution_with_ratings` - Returns correct counts
3. `test_rating_distribution_all_ratings_present` - Always returns ratings 1-5
4. `test_rating_distribution_total_matches_sum` - Total equals sum of counts
5. `test_rating_distribution_requires_auth` - Returns 401 without token

### Test Data Setup
```python
# Create ratings with known distribution
ratings_to_create = [
    (1, 2),   # 2 one-star ratings
    (2, 5),   # 5 two-star ratings
    (3, 10),  # 10 three-star ratings
    (4, 8),   # 8 four-star ratings
    (5, 3),   # 3 five-star ratings
]
# Total: 28 ratings
```

## Acceptance Criteria
- [ ] Endpoint returns 200 with distribution for authenticated user
- [ ] Endpoint returns 401 for unauthenticated requests
- [ ] Response always includes all 5 rating values (1-5)
- [ ] Counts are accurate for user's ratings
- [ ] Total matches sum of all counts
- [ ] Trailing slash on endpoint URL
- [ ] Schema documented with RESPONSE SHAPE comment
