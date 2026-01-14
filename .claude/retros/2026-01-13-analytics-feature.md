# Sprint Retrospective: Analytics Feature
**Date:** January 13, 2026
**Branch:** `feature/improvements`
**Commits:** `2d20372`, `b25297b`

---

## Summary

This session focused on building out a comprehensive analytics feature for the movie ranking application, including a GitHub-style activity chart and a genre distribution radar chart.

---

## What We Accomplished

### Features Delivered

1. **Analytics Page & Navigation**
   - New `/analytics` route with dedicated page
   - Header navigation tabs (Rankings | Analytics)

2. **Activity Chart (GitHub-style contribution grid)**
   - Rolling 12-month view with week-aligned start
   - 10px squares with 3-level intensity (1, 2, 3+ movies)
   - Future dates shown (dimmed) through end of current month
   - Smart month labels with overlap prevention
   - Tooltips on hover

3. **Genre Distribution Radar Chart**
   - SVG-based radar visualization
   - Top 6 genres displayed
   - Placeholder genres fill empty slots (Action, Comedy, Drama, Horror, Romance, Sci-Fi)
   - Primary genre per movie for accurate distribution

4. **Backend Analytics API**
   - `GET /api/v1/analytics/activity/` - rolling year activity data
   - `GET /api/v1/analytics/genres/` - genre distribution with primary genre logic

### Files Changed
- `app/routers/analytics.py` (new)
- `app/schemas/analytics.py` (new)
- `frontend/src/pages/AnalyticsPage.tsx` (new)
- `frontend/src/components/ActivityChart.tsx` (new)
- `frontend/src/components/GenreChart.tsx` (new)
- Plus updates to types, API client, CSS, and routing

---

## What Went Well

### Iterative Design
- Started with designer recommendation (horizontal bar chart for genres)
- Pivoted to radar chart based on user preference for visual interest
- Quick iteration cycles allowed for rapid refinement

### Bug Detection & Resolution
- Month label alignment issue caught during testing
- Root cause identified quickly (CSS flexbox ignoring `gridColumnStart`)
- Clean fix with absolute positioning

### Attention to Detail
- Overlap prevention for month labels (Dec/Jan edge case)
- Future dates shown but visually distinct
- Placeholder genres maintain chart shape consistency
- Activity levels tuned for realistic movie-watching behavior

### Code Quality
- Clean separation between frontend and backend
- Reusable chart components
- Proper TypeScript types throughout

---

## What Could Be Improved

### 1. CSS Layout Mismatch
**Issue:** Used `gridColumnStart` in a flexbox container, causing month labels to misalign.

**Root Cause:** Copy-paste from a grid-based example without verifying the parent container's display mode.

**Prevention:**
- Always verify parent container layout before using positioning properties
- Add CSS comments noting layout dependencies
- Consider creating a CSS architecture document

### 2. Initial Over-Engineering
**Issue:** Started with year filter dropdown, then removed it in favor of simpler rolling year.

**Learning:**
- Start with the simplest solution that meets the need
- Year filtering adds complexity without clear user value for this use case
- Ask clarifying questions earlier about scope

### 3. Activity Level Calibration
**Issue:** Initial ratio-based levels (25%, 50%, 75% of max) didn't make sense for typical usage where 1-2 movies/day is normal.

**Learning:**
- Consider real-world usage patterns when designing data visualizations
- Absolute thresholds often more intuitive than relative ones

### 4. Hot Reload Reliability
**Issue:** User reported changes not appearing despite HMR updates showing in console.

**Learning:**
- Recommend hard refresh (Cmd+Shift+R) when HMR seems stuck
- Consider adding cache-busting in development
- Server restart resolved the issue

---

## Bugs Encountered

| Bug | Cause | Fix | Time to Fix |
|-----|-------|-----|-------------|
| Month labels at wrong position | `gridColumnStart` ignored in flexbox | Switch to absolute positioning with calculated `left` | ~10 min |
| Dec/Jan labels overlapping | Labels too close at year boundary | Filter out earlier month if < 4 weeks apart | ~5 min |
| Genre counts inflated | Movies counted once per genre | Use only primary (first) genre | ~5 min |
| Activity colors too dim | Using rgba with low opacity | Switch to solid hex colors | ~2 min |

---

## Action Items

### Process Improvements
- [ ] Create CSS architecture guide documenting layout patterns used in the project
- [ ] Add visual regression testing for chart components
- [ ] Document chart component APIs for reuse

### Technical Debt
- [ ] Add unit tests for analytics endpoints
- [ ] Add component tests for ActivityChart and GenreChart
- [ ] Consider extracting radar chart as a generic reusable component

### Future Enhancements
- [ ] Add hover states to radar chart points showing movie details
- [ ] Consider adding average rating overlay to radar chart
- [ ] Add export/share functionality for analytics

---

## Team Reflections

### Frontend Engineering
> The radar chart implementation was a good learning experience in SVG coordinate math. The polar-to-cartesian conversion and polygon point generation are patterns we can reuse. Should consider building a small charting utility library.

### Backend Engineering
> The analytics queries are straightforward now but could become slow with large datasets. Consider adding database indexes on `rated_at` and potentially caching results. The GENRE_MAP constant should eventually move to a shared location or be fetched from TMDB.

### UX/Design
> The pivot from bar chart to radar chart worked out well visually. The placeholder genres maintain visual consistency even for new users. Consider adding an onboarding state that encourages users to rate movies across different genres.

### Overall
> Good session with clear communication and quick iterations. The bug with month label positioning highlighted the importance of understanding CSS layout modes. The feature is visually polished and ready for user feedback.

---

## Metrics

- **Session Duration:** ~1.5 hours
- **Features Completed:** 2 major (activity chart, genre chart)
- **Bugs Fixed:** 4
- **Iterations:** 8+ refinements based on feedback
- **Lines Changed:** ~1,600 additions

---

## Next Session Priorities

1. Run full test suite and fix any regressions
2. Consider mobile responsiveness for analytics page
3. Gather user feedback on chart usefulness
4. Potential: Add more analytics (watch streaks, rating distribution, etc.)
