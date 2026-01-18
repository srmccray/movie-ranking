# Quick Sketch: MovieCard Layout Redesign

**Created:** 2026-01-17
**Tier:** SMALL
**Triage Scores:** Complexity 3/10, Risk 2/10

## What

Redesign the MovieCard component layout to improve visual appeal and information hierarchy while maintaining all current functionality (star rating, date editing, kebab menu with delete action).

## Why

The current horizontal layout with poster-info-rating columns doesn't feel visually balanced. The star rating pushed to the right with padding to avoid the kebab menu creates awkward spacing. Users have expressed the card "doesn't look great" after recent positioning fixes.

## Current State Analysis

### Current Layout Structure
```
+------------------------------------------------------------------+
|  [Kebab Menu - absolute top-right]                               |
|                                                                  |
|  [Poster]  [Title                    ]  [Star Rating (5 stars)]  |
|  100x150   [Year                     ]                           |
|            [Genres                   ]                           |
|            [Rated Date (editable)    ]                           |
|                                                                  |
+------------------------------------------------------------------+
```

### Current Issues
1. **Horizontal stretch**: Three-column layout feels sparse on wide screens
2. **Awkward spacing**: `padding-top: var(--space-8)` on movie-actions to clear kebab menu
3. **Information density**: Large amount of horizontal space for minimal content
4. **Visual weight imbalance**: Small poster vs expansive empty middle area
5. **Star rating isolation**: Stars floating alone on the right feels disconnected

## Design Research: Industry Patterns

### Letterboxd
- **Card style**: Poster-dominant with overlay information
- **Rating**: Stars shown on hover or below poster
- **Actions**: Appear on hover
- **Takeaway**: Poster as hero element, progressive disclosure of details

### IMDb
- **Card style**: Horizontal with larger poster (2:3 ratio prominent)
- **Rating**: IMDb score badge with yellow background
- **Info hierarchy**: Title > Year > Runtime > Rating
- **Takeaway**: Strong visual hierarchy, rating as badge/chip

### Plex/Netflix
- **Card style**: Vertical poster cards in grid
- **Rating**: Percentage match or star overlay
- **Actions**: Play button overlay on hover
- **Takeaway**: Focus on poster, minimal metadata visible

### Spotify (for comparison)
- **Card style**: Album art + title + artist in compact rows
- **Actions**: Right-aligned contextual menu
- **Takeaway**: Tight vertical spacing, consistent row heights

## Layout Options

### Option A: Stacked Layout (Recommended)
```
+----------------------------------------+
|  [Poster 80x120] [Title          ] [...] |
|                  [Year - Genres  ]       |
|                  [5 Gold Stars   ]       |
|                  [Rated Jan 5, 2025 (edit)] |
+----------------------------------------+
```

**Changes:**
- Reduce poster to 80x120px (tighter fit)
- Stack all info vertically in middle column
- Move stars INTO the info section (below title/year)
- Rated date at bottom of info stack
- Kebab menu stays absolute top-right
- Remove dedicated `.movie-actions` column

**Pros:**
- More compact card height
- Better visual flow (top to bottom reading)
- Stars feel connected to movie info
- No awkward padding workaround needed

**Cons:**
- Requires restructuring JSX and CSS
- Stars may need smaller size (sm vs md)

### Option B: Two-Column with Rating Badge
```
+------------------------------------------+
|  [Poster    ] [Title               ] [...] |
|  100x150    ] [Year - Genres       ]       |
|              [Rated Jan 5, 2025 (edit)]   |
|  [4.5 Rating] [                    ]       |
|  [Badge     ]                             |
+------------------------------------------+
```

**Changes:**
- Convert star rating to numeric badge overlaid on poster bottom-left
- Remove right column entirely
- Two clean columns: poster + info

**Pros:**
- Very clean two-column layout
- Rating badge is compact and modern
- More room for longer titles

**Cons:**
- Loses interactive star rating (would need modal/popover)
- Significant UX change
- May confuse users expecting stars

### Option C: Enhanced Current Layout
```
+------------------------------------------------------------------+
|  [Poster]  [Title                        ]  [...] (kebab inline) |
|  100x150   [Year - Genres               ]                        |
|            [Rated Jan 5, 2025 (edit)     ]  [5 Gold Stars]       |
+------------------------------------------------------------------+
```

**Changes:**
- Move kebab menu inline with title row (not absolute positioned)
- Move stars to bottom-right, aligned with rated date
- Reduce overall card padding
- Tighten gap between columns

**Pros:**
- Minimal structural change
- Kebab and stars feel more grounded
- Preserves horizontal scan pattern

**Cons:**
- Still has three visual columns
- May still feel spread out

## Recommended Approach: Option A (Stacked Layout)

### Why Option A?
1. **Natural reading flow**: Eye moves top-to-bottom within info column
2. **Mobile-friendly**: Already collapsed for responsive
3. **Eliminates padding hack**: No need for space-8 padding-top
4. **Visual cohesion**: Stars feel part of the movie info, not isolated
5. **Compact**: Reduces visual noise, cards feel more intentional

### Implementation Plan

#### Step 1: Update JSX Structure
- Move `<StarRating>` from `.movie-actions` into `.movie-info`
- Place stars between title/year/genres and rated date
- Remove `.movie-actions` wrapper div
- Ensure kebab menu positioning unchanged

#### Step 2: Update CSS
- Remove `.movie-actions` styles
- Add `.movie-rating` styles within `.movie-info` context
- Adjust poster size to 80x120px
- Reduce card padding slightly
- Update star size from "md" to "sm"

#### Step 3: Responsive Adjustments
- Mobile already stacks; ensure stars fit in narrower layout
- Consider hiding genres on very small screens if needed

#### Step 4: Polish
- Test hover states
- Verify date editing still works
- Test delete confirmation overlay
- Ensure animations still apply

## Files Likely Affected

- `/Users/stephen/Projects/movie-ranking/frontend/src/components/MovieCard.tsx`
  - Move StarRating component into movie-info section
  - Remove movie-actions wrapper
  - Update star size prop to "sm"

- `/Users/stephen/Projects/movie-ranking/frontend/src/index.css`
  - Update `.movie-card` layout (remove space-between)
  - Remove `.movie-actions` styles
  - Add `.movie-rating` styles in info context
  - Update `.movie-poster` dimensions (80x120px)
  - Adjust responsive breakpoints

## Considerations

- **Accessibility**: Ensure star rating remains keyboard accessible in new position
- **Date editor width**: May need adjustment in narrower info column
- **Long titles**: Test with very long movie titles (already using text-overflow: ellipsis)
- **Animation timing**: Card entry animations should still work
- **AddMovieCard consistency**: May want to adjust its height to match new card height

## Acceptance Criteria

- [ ] MovieCard displays poster, title, year, genres, stars, and rated date in stacked layout
- [ ] Star rating is interactive and positioned below genres
- [ ] Kebab menu remains in top-right corner, opens correctly
- [ ] Delete confirmation overlay still covers entire card
- [ ] Date editing functionality works correctly
- [ ] Cards look balanced at desktop and mobile widths
- [ ] Hover effects (card lift, poster scale) still work
- [ ] AddMovieCard height is consistent with new MovieCard height

---

## Next Agent to Invoke

**Agent:** `frontend-implementation`

**Context to provide:**
- Feature slug: `moviecard-layout-redesign`
- Tier: SMALL
- Sketch location: `/Users/stephen/Projects/movie-ranking/.claude_docs/features/moviecard-layout-redesign/sketch.md`
- Approach: Option A (Stacked Layout) - move StarRating into movie-info section, remove movie-actions column
- Key files: MovieCard.tsx (lines 178-267 for JSX structure), index.css (lines 700-1100 for styles)

**After that agent completes:**
- Visual review of the new card layout
- Test all interactive elements (rating, date edit, delete)
- Consider follow-up for AddMovieCard height consistency if needed
