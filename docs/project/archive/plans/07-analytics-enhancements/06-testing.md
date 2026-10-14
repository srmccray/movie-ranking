# Task 06: Testing and Validation

## Agent
`qa-test-engineer`

## Objective
Verify all analytics enhancements work correctly through comprehensive backend and frontend testing.

## Backend Testing

### Test File
`tests/test_analytics.py` (new or extend existing)

### Stats Endpoint Tests

```python
class TestStatsEndpoint:
    """Tests for GET /api/v1/analytics/stats/ endpoint."""

    @pytest.mark.asyncio
    async def test_stats_returns_zeros_for_new_user(
        self, client: AsyncClient, auth_headers: dict
    ):
        """New user with no ratings should get all zeros."""
        response = await client.get(
            "/api/v1/analytics/stats/",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_movies"] == 0
        assert data["total_watch_time_minutes"] == 0
        assert data["average_rating"] == 0
        assert data["current_streak"] == 0
        assert data["longest_streak"] == 0

    @pytest.mark.asyncio
    async def test_stats_calculates_totals_correctly(
        self, client: AsyncClient, auth_headers: dict, test_movie: dict
    ):
        """Stats should accurately reflect user's ratings."""
        # Create multiple ratings
        for rating in [3, 4, 5]:
            response = await client.post(
                "/api/v1/rankings/",
                json={"movie_id": test_movie["movie_id"], "rating": rating},
                headers=auth_headers,
            )
            assert response.status_code == 201

        response = await client.get(
            "/api/v1/analytics/stats/",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_movies"] == 3
        assert data["average_rating"] == 4.0  # (3+4+5)/3

    @pytest.mark.asyncio
    async def test_stats_requires_authentication(self, client: AsyncClient):
        """Stats endpoint should require auth."""
        response = await client.get("/api/v1/analytics/stats/")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_stats_streak_calculation(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Verify streak calculation works correctly."""
        # This test would need to create ratings with specific dates
        # to verify streak logic
        pass  # Implement with date manipulation
```

### Rating Distribution Endpoint Tests

```python
class TestRatingDistributionEndpoint:
    """Tests for GET /api/v1/analytics/rating-distribution/ endpoint."""

    @pytest.mark.asyncio
    async def test_distribution_returns_all_ratings(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Distribution should include all 5 rating values."""
        response = await client.get(
            "/api/v1/analytics/rating-distribution/",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["distribution"]) == 5

        ratings = [d["rating"] for d in data["distribution"]]
        assert sorted(ratings) == [1, 2, 3, 4, 5]

    @pytest.mark.asyncio
    async def test_distribution_counts_correctly(
        self, client: AsyncClient, auth_headers: dict, test_movie: dict
    ):
        """Distribution counts should match actual ratings."""
        # Create known distribution: 2x3-star, 3x4-star, 1x5-star
        ratings_to_add = [3, 3, 4, 4, 4, 5]
        for rating in ratings_to_add:
            await client.post(
                "/api/v1/rankings/",
                json={"movie_id": test_movie["movie_id"], "rating": rating},
                headers=auth_headers,
            )

        response = await client.get(
            "/api/v1/analytics/rating-distribution/",
            headers=auth_headers,
        )

        data = response.json()
        dist_map = {d["rating"]: d["count"] for d in data["distribution"]}

        assert dist_map[1] == 0
        assert dist_map[2] == 0
        assert dist_map[3] == 2
        assert dist_map[4] == 3
        assert dist_map[5] == 1
        assert data["total"] == 6

    @pytest.mark.asyncio
    async def test_distribution_requires_authentication(self, client: AsyncClient):
        """Distribution endpoint should require auth."""
        response = await client.get("/api/v1/analytics/rating-distribution/")
        assert response.status_code == 401
```

## Frontend Testing

### MSW Handler Updates
Add to `frontend/src/__tests__/mocks/handlers.ts`:

```typescript
// Stats endpoint
http.get('/api/v1/analytics/stats/', ({ request }) => {
  const authHeader = request.headers.get('Authorization');
  if (!authHeader?.startsWith('Bearer ')) {
    return HttpResponse.json({ detail: 'Not authenticated' }, { status: 401 });
  }

  return HttpResponse.json({
    total_movies: 247,
    total_watch_time_minutes: 7620,
    average_rating: 3.8,
    current_streak: 12,
    longest_streak: 45,
  });
}),

// Rating distribution endpoint
http.get('/api/v1/analytics/rating-distribution/', ({ request }) => {
  const authHeader = request.headers.get('Authorization');
  if (!authHeader?.startsWith('Bearer ')) {
    return HttpResponse.json({ detail: 'Not authenticated' }, { status: 401 });
  }

  return HttpResponse.json({
    distribution: [
      { rating: 1, count: 6 },
      { rating: 2, count: 12 },
      { rating: 3, count: 41 },
      { rating: 4, count: 58 },
      { rating: 5, count: 42 },
    ],
    total: 159,
  });
}),
```

### Component Tests

#### StatsCard Tests
```typescript
// frontend/src/components/__tests__/StatsCard.test.tsx

describe('StatsCard', () => {
  it('renders all 4 metrics', () => {
    render(
      <StatsCard
        totalMovies={247}
        totalWatchTimeMinutes={7620}
        averageRating={3.8}
        currentStreak={12}
      />
    );

    expect(screen.getByText('247')).toBeInTheDocument();
    expect(screen.getByText(/127/)).toBeInTheDocument(); // hours
    expect(screen.getByText(/3.8/)).toBeInTheDocument();
    expect(screen.getByText(/12 day/)).toBeInTheDocument();
  });

  it('shows loading state', () => {
    render(<StatsCard {...defaultProps} isLoading={true} />);
    expect(screen.getByRole('status')).toBeInTheDocument(); // spinner
  });

  it('shows error state', () => {
    render(<StatsCard {...defaultProps} error="Failed to load" />);
    expect(screen.getByText('Failed to load')).toBeInTheDocument();
  });

  it('formats watch time correctly', () => {
    // Test various minute values
    const { rerender } = render(
      <StatsCard {...defaultProps} totalWatchTimeMinutes={45} />
    );
    expect(screen.getByText('45 min')).toBeInTheDocument();

    rerender(<StatsCard {...defaultProps} totalWatchTimeMinutes={120} />);
    expect(screen.getByText('2 hrs')).toBeInTheDocument();
  });

  it('handles zero streak', () => {
    render(<StatsCard {...defaultProps} currentStreak={0} />);
    expect(screen.getByText('No streak')).toBeInTheDocument();
  });
});
```

#### RatingDistributionChart Tests
```typescript
// frontend/src/components/__tests__/RatingDistributionChart.test.tsx

describe('RatingDistributionChart', () => {
  const mockDistribution = [
    { rating: 1, count: 6 },
    { rating: 2, count: 12 },
    { rating: 3, count: 41 },
    { rating: 4, count: 58 },
    { rating: 5, count: 42 },
  ];

  it('renders all 5 rating bars', () => {
    render(
      <RatingDistributionChart distribution={mockDistribution} total={159} />
    );

    // Check for 5 star labels
    expect(screen.getByLabelText('1 stars')).toBeInTheDocument();
    expect(screen.getByLabelText('5 stars')).toBeInTheDocument();
  });

  it('displays correct counts', () => {
    render(
      <RatingDistributionChart distribution={mockDistribution} total={159} />
    );

    expect(screen.getByText('58')).toBeInTheDocument(); // 4-star count
    expect(screen.getByText('159 movies rated')).toBeInTheDocument();
  });

  it('orders bars from 5 stars to 1 star', () => {
    render(
      <RatingDistributionChart distribution={mockDistribution} total={159} />
    );

    const rows = screen.getAllByRole('progressbar');
    // First bar should be 5-star (index 0)
    expect(rows[0]).toHaveAttribute('aria-valuenow', '42');
  });

  it('shows loading state', () => {
    render(
      <RatingDistributionChart
        distribution={[]}
        total={0}
        isLoading={true}
      />
    );
    expect(screen.getByRole('status')).toBeInTheDocument();
  });
});
```

### Integration Tests

```typescript
// frontend/src/__tests__/AnalyticsPage.test.tsx

describe('AnalyticsPage', () => {
  it('renders all 4 analytics cards', async () => {
    render(<AnalyticsPage />);

    // Wait for all cards to load
    await waitFor(() => {
      expect(screen.getByText('Activity')).toBeInTheDocument();
      expect(screen.getByText('Your Stats')).toBeInTheDocument();
      expect(screen.getByText('Genre Distribution')).toBeInTheDocument();
      expect(screen.getByText('Rating Distribution')).toBeInTheDocument();
    });
  });

  it('handles partial API failures gracefully', async () => {
    // Override one handler to return error
    server.use(
      http.get('/api/v1/analytics/stats/', () => {
        return HttpResponse.json({ detail: 'Server error' }, { status: 500 });
      })
    );

    render(<AnalyticsPage />);

    // Other cards should still render
    await waitFor(() => {
      expect(screen.getByText('Activity')).toBeInTheDocument();
      expect(screen.getByText('Genre Distribution')).toBeInTheDocument();
    });

    // Stats card should show error
    expect(screen.getByText(/Failed to load/)).toBeInTheDocument();
  });
});
```

## Manual Testing Checklist

### Desktop (>1024px)
- [ ] All 4 cards visible in 2x2 grid
- [ ] Row 1: Activity chart is wider than stats card
- [ ] Row 2: Genre and distribution charts are equal width
- [ ] Cards have consistent styling (borders, shadows, radius)
- [ ] No horizontal scrolling

### Tablet (768px - 1024px)
- [ ] Cards stack vertically
- [ ] Full width cards
- [ ] Activity chart may have horizontal scroll

### Mobile (<768px)
- [ ] Cards stack vertically
- [ ] Touch-friendly (no hover-only interactions)
- [ ] Text is readable

### Data Accuracy
- [ ] Total movies matches rankings count
- [ ] Average rating is mathematically correct
- [ ] Streak counts consecutive days correctly
- [ ] Rating distribution sums to total
- [ ] Watch time calculation correct (sum of runtimes)

### Edge Cases
- [ ] New user sees zeros/empty states
- [ ] User with only 1 rating
- [ ] User with same rating for all movies
- [ ] Very long streak (>365 days)
- [ ] Movies with null runtime excluded from watch time

## Performance Testing
- [ ] Page loads in <2 seconds on 3G
- [ ] No unnecessary re-renders
- [ ] API calls are parallelized

## Acceptance Criteria
- [ ] All backend tests pass
- [ ] All frontend tests pass
- [ ] Manual testing checklist complete
- [ ] No TypeScript errors
- [ ] No console errors in browser
- [ ] Lighthouse accessibility score >90
