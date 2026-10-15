# Frontend Development Guide

This document provides React/TypeScript development guidance for the Movie Ranking frontend application.

> **Important:** Before reading this guide, review the [root CLAUDE.md](../CLAUDE.md) for project-wide conventions including trailing slashes, datetime handling, HTTP status codes, and API contract verification. This guide focuses on frontend-specific patterns and implementation details.

## Project Overview

A React + TypeScript frontend built with Vite, featuring:
- React Router for navigation
- Context API for authentication state
- Custom hooks for data fetching
- Modular plain CSS with custom properties (dark "cinematic" theme)
- TMDB-backed movie search, analytics dashboard (hand-built SVG/CSS charts, no chart library), Amazon Prime CSV import wizard
- Email/password and Google OAuth sign-in, with automatic logout on any API 401
- Vitest + React Testing Library + MSW for tests

Scripts (`package.json`): `npm run dev` (port 3000, proxies `/api` to `localhost:8000`), `build` (`tsc -b && vite build`), `lint`, `test` (watch), `test:run`, `test:coverage`, `test:e2e` (Playwright, see "End-to-End Tests" under Testing Patterns).

## Project Structure

```
frontend/src/
├── api/
│   ├── client.ts          # API client singleton with typed methods
│   └── client.test.ts
├── components/
│   ├── index.ts           # Barrel exports (see note below for exceptions)
│   ├── Button.tsx         # Reusable button with variants
│   ├── Input.tsx          # Form input with label and error handling
│   ├── Modal.tsx          # Accessible modal dialog
│   ├── Header.tsx         # App header with nav (Rankings/Analytics/Settings) and logout
│   ├── StarRating.tsx     # Interactive star rating component
│   ├── MovieCard.tsx      # Movie display with actions
│   ├── AddMovieCard.tsx   # "Add a movie" placeholder card
│   ├── AddMovieForm.tsx   # Add-movie form (search / selected / manual modes)
│   ├── MovieSearch.tsx    # Debounced TMDB search with keyboard navigation
│   ├── EmptyState.tsx     # Empty state placeholder
│   ├── ProtectedRoute.tsx # Auth route wrapper
│   ├── GoogleSignInButton.tsx    # Google-branded sign-in/sign-up button
│   ├── StatsCard.tsx             # Analytics summary stats
│   ├── RatingDistributionChart.tsx  # Analytics rating bars
│   ├── ActivityChart.tsx         # Analytics activity heatmap (not in barrel)
│   ├── GenreChart.tsx            # Analytics genre radar chart (not in barrel)
│   ├── ImportWizard.tsx          # Amazon Prime import: orchestrates the 3 steps
│   ├── ImportFileUpload.tsx      # Import step 1: CSV upload
│   ├── ImportReview.tsx          # Import step 2: review/rate/skip/re-match movies
│   └── ImportComplete.tsx        # Import step 3: summary
├── context/
│   ├── AuthContext.tsx    # Authentication provider and hook
│   └── AuthContext.test.tsx
├── hooks/
│   └── useRankings.ts     # Rankings data hook with CRUD operations
├── pages/
│   ├── LoginPage.tsx           # Login form + Google sign-in
│   ├── RegisterPage.tsx        # Registration form + Google sign-up
│   ├── GoogleCallbackPage.tsx  # Receives ?token= from backend after Google OAuth
│   ├── RankingsPage.tsx        # Main rankings display page
│   ├── AnalyticsPage.tsx       # Stats, activity, genres, rating distribution
│   └── SettingsPage.tsx        # Profile, Google linking, import wizard, clear rankings
├── styles/                # Modular CSS (see Styling Conventions)
│   ├── index.css          # Imports everything in cascade order
│   ├── variables.css      # Design tokens
│   ├── base.css, utilities.css
│   ├── components/        # buttons, forms, cards, header, modal, movie-card, star-rating, alerts
│   └── pages/             # auth, rankings, analytics, settings, import
├── types/
│   └── index.ts           # All TypeScript interfaces
├── __tests__/
│   ├── setup.ts           # Vitest setup: jest-dom, MSW server, localStorage + matchMedia mocks
│   ├── SettingsPage.test.tsx
│   └── mocks/
│       ├── handlers.ts    # MSW handlers (`handlers` + `importHandlers`) and mock-data helpers
│       └── server.ts      # MSW server instance
├── App.tsx                # Root component with routing
└── main.tsx               # Application entry point (imports styles/index.css)
```

Unit/component tests are colocated (`*.test.ts(x)` next to the source); `__tests__/` holds setup, mocks, and page-level tests.

### Routes (`App.tsx`)

| Path | Page | Access |
|------|------|--------|
| `/login`, `/register` | `LoginPage`, `RegisterPage` | Public |
| `/auth/google/callback` | `GoogleCallbackPage` | Public |
| `/` | `RankingsPage` | Protected |
| `/rankings` | Redirects to `/` | Protected |
| `/analytics` | `AnalyticsPage` | Protected |
| `/settings` | `SettingsPage` | Protected |
| `*` | Redirects to `/` | - |

`ProtectedRoute` shows a spinner while `isLoading`, then redirects unauthenticated users to `/login` with `state={{ from: location }}`.

## Adding a New Component

### 1. Create the Component File

Create `/frontend/src/components/NewComponent.tsx`:

```tsx
import type { ReactNode } from 'react';

// 1. Define props interface extending HTML attributes when applicable
interface NewComponentProps {
  title: string;
  children: ReactNode;
  variant?: 'default' | 'highlighted';
  onAction?: () => void;
}

// 2. Use named export (not default)
export function NewComponent({
  title,
  children,
  variant = 'default',
  onAction,
}: NewComponentProps) {
  // 3. Build class names dynamically
  const classes = [
    'new-component',
    `new-component-${variant}`,
  ].filter(Boolean).join(' ');

  return (
    <div className={classes}>
      <h3 className="new-component-title">{title}</h3>
      <div className="new-component-content">{children}</div>
      {onAction && (
        <button
          className="btn btn-primary"
          onClick={onAction}
          aria-label={`Action for ${title}`}
        >
          Take Action
        </button>
      )}
    </div>
  );
}
```

### 2. Export from Barrel File

Add to `/frontend/src/components/index.ts`:

```tsx
export { NewComponent } from './NewComponent';
```

Note: `ActivityChart` and `GenreChart` are not in the barrel; `AnalyticsPage` imports them directly from their files.

### 3. Add Component Styles

Create `/frontend/src/styles/components/new-component.css` and add an `@import './components/new-component.css';` line to `/frontend/src/styles/index.css` (in the Components block, before Pages and utilities). Do not add styles to the legacy `src/index.css`.

```css
/* New Component */
.new-component {
  background-color: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-4);
}

.new-component-highlighted {
  border-color: var(--color-primary-500);
}

/* NOTE: the neutral scale is inverted for the dark theme: 50 is lightest
   (text), 900 is darkest. */

.new-component-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--color-neutral-50);
  margin-bottom: var(--space-2);
}

.new-component-content {
  color: var(--color-neutral-300);
}
```

### Component Patterns to Follow

1. **Props Interface**: Always define a TypeScript interface for props
2. **Named Exports**: Use `export function ComponentName` not `export default`
3. **Accessibility**: Include ARIA attributes, keyboard handlers, proper roles
4. **Variants via Props**: Use `variant` prop for style variations
5. **Dynamic Classes**: Build class strings from arrays, filter empty values
6. **Optional Callbacks**: Check existence before rendering action elements

### Extending HTML Elements

For components wrapping HTML elements, extend native attributes (simplified from the real `Button.tsx`, which also supports `size` and `fullWidth`):

```tsx
import type { ButtonHTMLAttributes, ReactNode } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  fullWidth?: boolean;
  children: ReactNode;
}

export function Button({
  variant = 'primary',
  loading = false,
  disabled,
  className = '',
  children,
  ...props  // Spread remaining HTML attributes
}: ButtonProps) {
  return (
    <button
      className={`btn btn-${variant} ${className}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? <span className="spinner" /> : children}
    </button>
  );
}
```

## Adding a New Page

### 1. Create the Page Component

Create `/frontend/src/pages/NewFeaturePage.tsx`:

```tsx
import { useState, useEffect, useCallback } from 'react';
import { Header, Button, EmptyState, Modal } from '../components';
// (types such as CreateData, and ItemCard/NewItemForm, are placeholders)
import { useNewFeature } from '../hooks/useNewFeature';

export function NewFeaturePage() {
  const {
    items,
    isLoading,
    error,
    fetchItems,
    createItem,
  } = useNewFeature();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Fetch data on mount
  useEffect(() => {
    fetchItems();
  }, []);

  const handleOpenModal = useCallback(() => {
    setIsModalOpen(true);
  }, []);

  const handleCloseModal = useCallback(() => {
    setIsModalOpen(false);
  }, []);

  const handleCreate = useCallback(async (data: CreateData) => {
    setActionError(null);
    try {
      await createItem(data);
      setIsModalOpen(false);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to create');
    }
  }, [createItem]);

  const showEmptyState = !isLoading && items.length === 0 && !error;
  const showItems = items.length > 0;

  return (
    <>
      <Header />
      <main className="main-layout">
        <div className="container">
          <div className="page-content">
            {/* Page Header */}
            <div className="page-header">
              <h1 className="page-title">New Feature</h1>
              <Button onClick={handleOpenModal}>Add Item</Button>
            </div>

            {/* Error Alert */}
            {error && (
              <div className="alert alert-error" role="alert">
                {error}
                <Button variant="ghost" size="sm" onClick={() => fetchItems()}>
                  Retry
                </Button>
              </div>
            )}

            {/* Loading State */}
            {isLoading && items.length === 0 && (
              <div className="loading-container">
                <div className="spinner" />
              </div>
            )}

            {/* Empty State */}
            {showEmptyState && (
              <EmptyState
                title="No items yet"
                description="Start by adding your first item."
                action={{
                  label: 'Add First Item',
                  onClick: handleOpenModal,
                }}
              />
            )}

            {/* Items List */}
            {showItems && (
              <div className="items-list">
                {items.map((item) => (
                  <ItemCard key={item.id} item={item} />
                ))}
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        title="Add New Item"
      >
        <NewItemForm onSubmit={handleCreate} onCancel={handleCloseModal} />
      </Modal>
    </>
  );
}
```

### 2. Add Route to App.tsx

Update `/frontend/src/App.tsx`:

```tsx
import { NewFeaturePage } from './pages/NewFeaturePage';

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/auth/google/callback" element={<GoogleCallbackPage />} />

          {/* Protected routes */}
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<RankingsPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/new-feature" element={<NewFeaturePage />} />
          </Route>

          {/* Catch all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
```

If the page should appear in the header nav, also add a `NavLink` in `components/Header.tsx`.

### Page Structure Pattern

Every page follows this structure:
1. **Header**: Always include the `<Header />` component
2. **Main Layout**: Wrap content in `<main className="main-layout">`
3. **Container**: Use `<div className="container">` for max-width
4. **Page Content**: Use `<div className="page-content">` for padding
5. **States**: Handle loading, error, empty, and success states

## Adding a New Custom Hook

### 1. Create the Hook File

Create `/frontend/src/hooks/useNewFeature.ts`:

```tsx
import { useState, useCallback } from 'react';
import { apiClient, ApiClientError } from '../api/client';
import type { NewItem, NewItemCreate } from '../types';

interface UseNewFeatureReturn {
  items: NewItem[];
  isLoading: boolean;
  error: string | null;
  fetchItems: () => Promise<void>;
  createItem: (data: NewItemCreate) => Promise<void>;
  updateItem: (id: string, data: Partial<NewItemCreate>) => Promise<void>;
  deleteItem: (id: string) => Promise<void>;
}

export function useNewFeature(): UseNewFeatureReturn {
  const [items, setItems] = useState<NewItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchItems = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.getNewItems();
      setItems(response.items);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else {
        setError('Failed to load items');
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  const createItem = useCallback(async (data: NewItemCreate) => {
    setError(null);

    try {
      const newItem = await apiClient.createNewItem(data);
      setItems((prev) => [newItem, ...prev]);
    } catch (err) {
      if (err instanceof ApiClientError) {
        throw err;  // Re-throw for component to handle
      }
      throw new Error('Failed to create item');
    }
  }, []);

  const updateItem = useCallback(async (id: string, data: Partial<NewItemCreate>) => {
    setError(null);

    try {
      const updated = await apiClient.updateNewItem(id, data);
      setItems((prev) =>
        prev.map((item) => (item.id === id ? updated : item))
      );
    } catch (err) {
      if (err instanceof ApiClientError) {
        throw err;
      }
      throw new Error('Failed to update item');
    }
  }, []);

  const deleteItem = useCallback(async (id: string) => {
    setError(null);

    try {
      await apiClient.deleteNewItem(id);
      setItems((prev) => prev.filter((item) => item.id !== id));
    } catch (err) {
      if (err instanceof ApiClientError) {
        throw err;
      }
      throw new Error('Failed to delete item');
    }
  }, []);

  return {
    items,
    isLoading,
    error,
    fetchItems,
    createItem,
    updateItem,
    deleteItem,
  };
}
```

### Hook Patterns to Follow

1. **Return Interface**: Define explicit return type interface
2. **State Management**: Use `useState` for items, loading, error
3. **useCallback**: Wrap all functions in `useCallback`
4. **Error Handling**:
   - Set local error state for fetch failures
   - Re-throw errors for mutations (let component handle UI feedback)
5. **Optimistic Updates**: Update local state after successful API calls
6. **ApiClientError Check**: Always check `instanceof ApiClientError`

## Adding API Endpoints

### 1. Add Types

Update `/frontend/src/types/index.ts`:

```tsx
// API Response Types
export interface NewItem {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface NewItemListResponse {
  items: NewItem[];
  total: number;
  limit: number;
  offset: number;
}

// Request Types
export interface NewItemCreate {
  name: string;
  description?: string | null;
}

export interface NewItemUpdate {
  name?: string;
  description?: string | null;
}
```

### 2. Add API Methods

Update `/frontend/src/api/client.ts`:

```tsx
import type {
  // ... existing imports
  NewItem,
  NewItemListResponse,
  NewItemCreate,
  NewItemUpdate,
} from '../types';

class ApiClient {
  // ... existing methods

  // New Item endpoints - NOTE: All URLs must have trailing slashes (see root CLAUDE.md)
  async getNewItems(limit = 20, offset = 0): Promise<NewItemListResponse> {
    return this.request<NewItemListResponse>(
      `/new-items/?limit=${limit}&offset=${offset}`
    );
  }

  async createNewItem(data: NewItemCreate): Promise<NewItem> {
    return this.request<NewItem>('/new-items/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateNewItem(id: string, data: NewItemUpdate): Promise<NewItem> {
    return this.request<NewItem>(`/new-items/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteNewItem(id: string): Promise<void> {
    await this.request<void>(`/new-items/${id}/`, {
      method: 'DELETE',
    });
  }
}
```

### Content-Type Rules

- **JSON requests** (default): Automatically set to `application/json`
- **Form data** (login only): Use `application/x-www-form-urlencoded`
- **File upload** (`uploadAmazonPrimeCSV`): `multipart/form-data` via `FormData`; do NOT set Content-Type manually (the browser adds the boundary). It uses its own `fetch` call rather than `request()`
- **Delete requests**: No Content-Type needed (no body)

**Trailing-slash exceptions:** `/auth/login` and `/auth/register` are the only routes WITHOUT a trailing slash, because the backend declares them that way (`app/routers/auth.py`). Every other endpoint has one.

```tsx
// Login uses form-urlencoded
async login(email: string, password: string): Promise<Token> {
  const formData = new URLSearchParams();
  formData.append('username', email);
  formData.append('password', password);

  return this.request<Token>('/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData.toString(),
  });
}
```

### Existing API Client Methods

`apiClient` (`src/api/client.ts`) exposes: `register`, `login`, `getGoogleAuthUrl`, `getGoogleLinkUrl`, `getCurrentUser`, `createMovie`, `searchMovies`, `createOrUpdateRanking`, `getRankings`, `deleteRanking`, `clearAllRankings`, `getActivity`, `getGenres`, `getStats`, `getRatingDistribution`, `uploadAmazonPrimeCSV`, `getImportSession`, `addImportMovie`, `skipImportMovie`, `cancelImportSession`, `updateImportMovieMatch`. The base path is the hardcoded constant `API_BASE = '/api/v1'`. There is no client method for updating a ranking's rating or `rated_at`; `useRankings.updateRating` and `updateRatedAt` go through `createOrUpdateRanking` (POST upsert).

### 401 Auto-Logout

`ApiClient` holds an `onUnauthorized` callback (`setOnUnauthorized`). Any non-OK response with status 401 invokes it before the error is thrown. `AuthProvider` registers `logout` as that callback, which clears the token, so `ProtectedRoute` then redirects to `/login`. Do not add per-call 401 handling for session expiry. Note this applies to failed login attempts too (a 401 from `/auth/login` also triggers `logout`, which is harmless when already logged out).

### Handling 204 No Content

The API client already handles 204 responses:

```tsx
// In client.ts request method
if (response.status === 204) {
  return undefined as T;
}
```

## Type Organization

Types are organized in `/frontend/src/types/index.ts`:

```tsx
// API Response Types (what the API returns)
export interface Entity {
  id: string;
  // ... fields matching API response
  created_at: string;  // ISO 8601 strings from API
  updated_at: string;
}

// Brief/Nested Types (for embedded objects)
export interface EntityBrief {
  id: string;
  name: string;  // Only essential fields
}

// List Response Types (paginated endpoints)
export interface EntityListResponse {
  items: Entity[];
  total: number;
  limit: number;
  offset: number;
}

// Request Types (what we send to API)
export interface EntityCreate {
  name: string;
  optional_field?: string | null;
}

export interface EntityUpdate {
  name?: string;  // All fields optional for PATCH
  optional_field?: string | null;
}

// Error Types
export interface ApiError {
  detail: string | ValidationError[];
}

export interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

// Context/State Types
export interface SomeContextType {
  data: Entity[];
  isLoading: boolean;
  someAction: (id: string) => Promise<void>;
}
```

### Type Conventions

1. **Dates**: Use `string` type for dates (ISO 8601 from API)
2. **Optional/Nullable**: Use `field?: type | null` pattern
3. **IDs**: Always `string` (UUIDs from backend)
4. **Response vs Request**: Separate types for API responses and requests
5. **Field names**: Use `snake_case` to match backend JSON (see root CLAUDE.md)

## API Contract Verification (Frontend-Specific)

> **Note:** See the [root CLAUDE.md](../CLAUDE.md) for the complete API contract verification checklist. This section covers frontend-specific patterns.

### Type Mapping Process

1. **Find the backend schema:**
   ```bash
   # Look in app/schemas/<entity>.py for response types
   cat app/schemas/movie.py | grep -A 20 "class.*Response"
   ```

2. **Check the router's response_model:**
   ```bash
   # Look in app/routers/<entities>.py
   grep "response_model=" app/routers/movies.py
   ```

3. **Create matching frontend type:**
   ```typescript
   // Backend: TMDBSearchResponse with results, query, year
   // Frontend must match exactly:
   export interface TMDBSearchResponse {
     results: TMDBSearchResult[];
     query: string;
     year: number | null;
   }
   ```

4. **Use the wrapper type in API client:**
   ```typescript
   // CORRECT - uses full response type, then extracts what's needed
   async searchMovies(query: string, year?: number): Promise<TMDBSearchResult[]> {
     const response = await this.request<TMDBSearchResponse>(`/movies/search/?...`);
     return response.results;
   }

   // WRONG - assumes backend returns array directly
   async searchMovies(query: string, year?: number): Promise<TMDBSearchResult[]> {
     return this.request<TMDBSearchResult[]>(`/movies/search/?...`);
   }
   ```

### Common Frontend Mistakes

1. **Assuming list endpoints return arrays directly**
   ```typescript
   // WRONG - most list endpoints return wrapper objects
   async getItems(): Promise<Item[]> {
     return this.request<Item[]>('/items/');
   }

   // CORRECT - list endpoints return paginated response
   async getItems(): Promise<ItemListResponse> {
     return this.request<ItemListResponse>('/items/');
   }
   ```

2. **Not defining wrapper response types**
   ```typescript
   // WRONG - only has the item type
   export interface TMDBSearchResult { ... }

   // CORRECT - has both item AND response wrapper types
   export interface TMDBSearchResult { ... }
   export interface TMDBSearchResponse {
     results: TMDBSearchResult[];
     query: string;
     year: number | null;
   }
   ```

Import-related wrapper types (`ImportSessionResponse`, `ImportSessionDetailResponse`, `MatchedMovieItem`, `ImportMovieAddRequest`, `ImportMovieMatchRequest`) mirror `app/schemas/import_amazon.py`; analytics types (`ActivityResponse`, `GenreResponse`, `StatsResponse`, `RatingDistributionResponse`) mirror `app/schemas/analytics.py`.

### Testing API Integrations

When adding MSW handlers, match the backend response shape exactly:

```typescript
// handlers.ts - must match backend TMDBSearchResponse schema
http.get('/api/v1/movies/search/', () => {
  return HttpResponse.json({
    results: [{ tmdb_id: 1, title: 'Test', year: 2024, poster_url: null, overview: null }],
    query: 'test',
    year: null,
  });
});
```

## Styling Conventions

### Design Tokens

CSS is modular. `main.tsx` imports `/frontend/src/styles/index.css`, which `@import`s files in cascade order: `variables.css` (tokens), `base.css`, `components/*.css`, `pages/*.css`, then `utilities.css` last. Put new styles in the matching file (or add a new file and import it).

The theme is a dark "cinematic" theme. All styling uses CSS custom properties defined in `/frontend/src/styles/variables.css` (excerpt; see the file for the full set):

```css
:root {
  /* Colors */
  --color-bg-base / -primary / -secondary / -tertiary / -accent  /* dark layers */
  --color-primary-500: #a855f7;   /* purple accent (50-200 are translucent, 600-700 darker) */
  --color-secondary-500: #3b82f6; /* blue accent */
  --color-highlight: #22d3ee;
  --color-neutral-50 ... -900     /* INVERTED: 50 = lightest (text), 900 = darkest */
  --color-success / --color-warning / --color-error (+ -bg variants)
  --color-border, --color-border-hover, --color-border-focus
  --color-star-filled: #fbbf24;
  --gradient-primary, --glass-bg, --glass-blur

  /* Spacing (4px base) */
  --space-1: 0.25rem;   /* 4px */
  --space-2: 0.5rem;    /* 8px */
  --space-3: 0.75rem;   /* 12px */
  --space-4: 1rem;      /* 16px */
  --space-5 / --space-6: 1.5rem / --space-8: 2rem / --space-10 / --space-12

  /* Border Radius */
  --radius-sm: 0.25rem;
  --radius-md: 0.5rem;
  --radius-lg: 0.75rem;
  --radius-xl: 1rem;
  --radius-2xl: 1.25rem;

  /* Shadows */
  --shadow-sm / --shadow-md / --shadow-lg / --shadow-xl
  --shadow-card, --shadow-card-hover, --shadow-glow-purple, --shadow-glow-blue

  /* Misc */
  --font-family, --transition-fast (150ms) / -normal (200ms) / -slow (300ms)
}
```

### Style Patterns

**Always use CSS custom properties:**

```css
/* CORRECT */
.component {
  padding: var(--space-4);
  color: var(--color-neutral-100);
  border-radius: var(--radius-lg);
}

/* WRONG - hardcoded values */
.component {
  padding: 16px;
  color: #e0e0e8;
  border-radius: 8px;
}
```

### Available Component Classes

```css
/* Buttons */
.btn, .btn-primary, .btn-secondary, .btn-ghost, .btn-danger
.btn-sm, .btn-md, .btn-lg
.btn-full (full width)
.btn-icon (icon-only button)
.btn-google (used by GoogleSignInButton)

/* Forms */
.form-group, .form-label, .form-input, .form-error

/* Cards */
.card, .card-sm, .card-md, .card-lg

/* Alerts */
.alert, .alert-error, .alert-success

/* Layout */
.container, .main-layout, .page-content, .page-header, .page-title

/* States */
.loading-container, .spinner, .empty-state

/* Misc */
.badge, .badge-success, .badge-neutral
```

Page-specific classes live in `styles/pages/*.css` (e.g. `auth-layout`/`auth-card`, analytics, import wizard).

### Adding New Styles

Add styles to the appropriate file under `/frontend/src/styles/` (`components/` for reusable components, `pages/` for page-specific) following existing patterns:

```css
/* New Feature Component */
.new-feature {
  /* Use existing tokens */
  background-color: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-4);
  box-shadow: var(--shadow-sm);
}

.new-feature:hover {
  border-color: var(--color-border-hover);
}

/* Responsive adjustments */
@media (max-width: 640px) {
  .new-feature {
    padding: var(--space-3);
  }
}
```

## State Management Patterns

### Authentication State

Uses Context API via `AuthContext`:

```tsx
import { useAuth } from '../context/AuthContext';

function Component() {
  const { token, isAuthenticated, isLoading, login, logout, register, loginWithToken } = useAuth();

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }

  return <AuthenticatedContent />;
}
```

- The JWT is stored in `localStorage` under `movie_ranking_token` and mirrored into `apiClient` via `setToken`.
- `loginWithToken(token)` stores a token obtained out-of-band; `GoogleCallbackPage` uses it.
- `useAuth()` throws if used outside `AuthProvider`.

### Google OAuth Flow

1. `LoginPage`/`RegisterPage` render `GoogleSignInButton` (props: `variant: 'signin' | 'signup'`, `loading`, `fullWidth`, plus button attributes). Clicking calls `apiClient.getGoogleAuthUrl()` (passes `redirect_uri=<origin>/auth/google/callback`) and sets `window.location.href` to the returned `authorization_url`.
2. The backend completes OAuth and redirects to `/auth/google/callback?token=...` (or `?error=...&error_description=...`).
3. `GoogleCallbackPage` calls `loginWithToken(token)` and navigates to `/` (or shows an error with a link back to `/login`).
4. Account linking for existing users happens on `SettingsPage` via `apiClient.getGoogleLinkUrl()` (redirect back to `/settings`) and `getCurrentUser()` (`UserProfileResponse.auth_provider`: `'local' | 'google' | 'linked'`).

### Amazon Prime Import Wizard

`SettingsPage` opens `ImportWizard` (`onClose`, optional `onComplete`). It is a three-step state machine (`upload` -> `review` -> `complete`) and owns the session state:

- `ImportFileUpload` (`onUploadComplete(session)`) calls `uploadAmazonPrimeCSV`.
- `ImportReview` (`movies`, `currentIndex`, `sessionId`, `onAdd`, `onSkip`, `onComplete`, `onMovieUpdated`) lets the user rate/add or skip each matched movie, and re-match via TMDB search (`updateImportMovieMatch`).
- `ImportComplete` (`addedCount`, `skippedCount`, `unmatchedTitles`, `onDone`) shows the summary.
- Cancelling calls `cancelImportSession` (errors ignored). Add/skip go to `addImportMovie` / `skipImportMovie` by session id + movie index.

### Analytics Page

`AnalyticsPage` fetches `getActivity`, `getGenres`, `getStats`, `getRatingDistribution` in parallel with `Promise.allSettled`, tracking loading and error state per section so one failure does not blank the page. Presentational components take data as props: `StatsCard`, `RatingDistributionChart` (has `isLoading`/`error` props), `ActivityChart` (heatmap; `activity`, `startDate`, `endDate`), `GenreChart` (radar; `genres`, `totalMovies`). Charts are plain SVG/CSS; there is no charting dependency.

### Feature Data State

Uses custom hooks with local state:

```tsx
import { useRankings } from '../hooks/useRankings';

function Component() {
  const {
    rankings,      // Data array
    total,         // Total count
    isLoading,     // Loading state
    error,         // Error message or null
    hasMore,       // Pagination flag
    sortBy, sortOrder, setSort, // Server-side sorting (SortField / SortOrder)
    fetchRankings, // Fetch/refresh function (pass true to reset to page 1)
    loadMore,      // Pagination function (page size 10)
    addMovieAndRank,
    updateRating,
    updateRatedAt,
    deleteRanking,
  } = useRankings();
}
```

### Form State

Uses local `useState` within form components:

```tsx
function FormComponent({ onSubmit, onCancel }: Props) {
  const [fieldValue, setFieldValue] = useState('');
  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const validate = (): boolean => {
    const newErrors: FormErrors = {};
    if (!fieldValue.trim()) {
      newErrors.field = 'Field is required';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);

    if (!validate()) return;

    setIsSubmitting(true);
    try {
      await onSubmit({ field: fieldValue });
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed');
    } finally {
      setIsSubmitting(false);
    }
  };
}
```

## Error Handling Patterns

### API Client Errors

The `ApiClientError` class wraps API errors:

```tsx
import { ApiClientError } from '../api/client';

try {
  await apiClient.someMethod();
} catch (err) {
  if (err instanceof ApiClientError) {
    // Handle API error
    console.error(`Status: ${err.status}, Message: ${err.message}`);

    // Check specific status codes
    if (err.status === 409) {
      setError('Resource already exists');
    } else if (err.status === 404) {
      setError('Resource not found');
    } else {
      setError(err.message);
    }
  } else {
    // Handle unexpected error
    setError('An unexpected error occurred');
  }
}
```

### Error Display Pattern

```tsx
{error && (
  <div className="alert alert-error" role="alert">
    {error}
    <Button
      variant="ghost"
      size="sm"
      onClick={() => fetchData()}
      style={{ marginLeft: 'var(--space-2)' }}
    >
      Retry
    </Button>
  </div>
)}
```

### Form Validation Errors

```tsx
interface FormErrors {
  email?: string;
  password?: string;
}

const validate = (): boolean => {
  const newErrors: FormErrors = {};

  if (!email.trim()) {
    newErrors.email = 'Email is required';
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    newErrors.email = 'Please enter a valid email';
  }

  if (!password) {
    newErrors.password = 'Password is required';
  } else if (password.length < 8) {
    newErrors.password = 'Password must be at least 8 characters';
  }

  setErrors(newErrors);
  return Object.keys(newErrors).length === 0;
};
```

## Testing Patterns

### Test File Location

Place tests next to the file being tested (existing examples: `MovieSearch.test.tsx`, `GoogleSignInButton.test.tsx`, `ProtectedRoute.test.tsx`, `AuthContext.test.tsx`, page tests, `api/client.test.ts`):

```
components/
  Button.tsx
  Button.test.tsx
```

Page-level tests may also live in `src/__tests__/` (e.g. `SettingsPage.test.tsx`).

### End-to-End Tests (Playwright, ADR-0006)

Gherkin scenarios from `docs/project/user_stories/accepted/` are automated with Playwright in `frontend/e2e/`. Vitest excludes `e2e/`.

```bash
cd frontend
npm install
npx playwright install chromium   # once per machine
npm run test:e2e                  # headless; also `npm run test:e2e:ui`
```

- Prerequisites: the repo-root `venv` with `requirements-test.txt` installed (provides `aiosqlite`). No Postgres, Docker, TMDB key, or network is needed.
- `playwright.config.ts` starts both servers itself: the real FastAPI app on a throwaway SQLite file (`e2e/support/run_backend.py`, port 8100) and Vite on port 3100 proxying `/api` to it (`API_PROXY_TARGET`). It never reuses a running dev server.
- Naming: one spec per story, `e2e/us-XXXX-<slug>.spec.ts`, `test.describe('US-XXXX: <title>')`, and one `test('Scenario: <name>')` per Gherkin scenario, with `Given/When/Then` comments. Cross-story smoke specs are `e2e/smoke-*.spec.ts`; shared helpers go in `e2e/support/`.
- ADR-0003 applies: drive the real UI and public API only. Setup is allowed via the UI or session injection (e.g. a token in `localStorage`); no DB access and no mocking of the app's own API. Flows needing TMDB (search, import) are not automated yet.
- Chromium only for now (ADR-0006 also names Firefox and WebKit).

### Running Tests

```bash
npm test                # Vitest watch mode
npm run test:run        # Single run (CI)
npm run test:coverage   # Single run with coverage
```

Config is in the `test` block of `vite.config.ts`: `jsdom` environment, globals enabled, setup file `src/__tests__/setup.ts` (starts the MSW server with `onUnhandledRequest: 'warn'`, resets handlers and clears `localStorage` after each test, mocks `localStorage` and `window.matchMedia`). Stack: Vitest, React Testing Library, `@testing-library/user-event`, `jest-dom`, MSW 2.

### MSW Mock Handlers

Add handlers in `/frontend/src/__tests__/mocks/handlers.ts` (the `handlers` array for core API; import-wizard routes are in `importHandlers`; `server.ts` combines both). The file also exports helpers such as `resetMockData`, `setTmdbServiceError`, `setUserGoogleLinked`, `addValidOAuthState`, `resetImportSessions`, `createMockImportSession`, and constants `MOCK_TOKEN`, `MOCK_USER_EMAIL`. Note there is currently no handler for `PATCH .../movie/:index/match/`, or for `analytics/activity|genres`, `rankings/all/`; add one if a test needs it.

```tsx
import { http, HttpResponse } from 'msw';

export const handlers = [
  http.get('/api/v1/new-items/', ({ request }) => {
    const authHeader = request.headers.get('Authorization');

    if (!authHeader?.startsWith('Bearer ')) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }

    return HttpResponse.json({
      items: [
        { id: '1', name: 'Item 1', created_at: '2024-01-01T00:00:00Z' },
      ],
      total: 1,
      limit: 20,
      offset: 0,
    });
  }),

  http.post('/api/v1/new-items/', async ({ request }) => {
    const authHeader = request.headers.get('Authorization');

    if (!authHeader?.startsWith('Bearer ')) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }

    const body = await request.json();

    return HttpResponse.json(
      {
        id: 'new-id',
        ...body,
        created_at: new Date().toISOString(),
      },
      { status: 201 }
    );
  }),
];
```

### Component Test Pattern

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from './Button';

describe('Button', () => {
  it('should render children', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole('button')).toHaveTextContent('Click me');
  });

  it('should call onClick when clicked', () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click me</Button>);

    fireEvent.click(screen.getByRole('button'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('should be disabled when loading', () => {
    render(<Button loading>Click me</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
  });
});
```

## Common Gotchas

> **Note:** For trailing slashes, datetime handling, and HTTP status codes, see the [root CLAUDE.md](../CLAUDE.md). This section covers frontend-specific gotchas.

### 1. Date Handling

Send dates as ISO 8601 UTC strings:

```tsx
// CORRECT
const ratedAt = new Date().toISOString();  // "2024-01-15T10:30:00.000Z"

// For date inputs, convert local date to ISO
const localDate = '2024-01-15';  // from <input type="date">
const isoDate = new Date(localDate).toISOString();
```

### 2. Login Content-Type

Login uses `application/x-www-form-urlencoded`, not JSON:

```tsx
async login(email: string, password: string): Promise<Token> {
  const formData = new URLSearchParams();
  formData.append('username', email);  // Note: 'username' not 'email'
  formData.append('password', password);

  return this.request<Token>('/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData.toString(),
  });
}
```

### 3. Component Imports

Always import from barrel file when available:

```tsx
// CORRECT
import { Button, Input, Modal } from '../components';

// AVOID
import { Button } from '../components/Button';
import { Input } from '../components/Input';
```

Exception: `ActivityChart` and `GenreChart` are not exported from the barrel; import them from their files.

### 4. Form Event Handling

Always prevent default and handle async properly:

```tsx
const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();  // Always prevent default
  setSubmitError(null);
  setIsSubmitting(true);

  try {
    await someAsyncAction();
  } catch (err) {
    setSubmitError(err instanceof Error ? err.message : 'Failed');
  } finally {
    setIsSubmitting(false);  // Always reset loading state
  }
};
```

### 5. useCallback Dependencies

Include all used functions in dependency arrays:

```tsx
// CORRECT
const handleAction = useCallback(async () => {
  await fetchData();
}, [fetchData]);

// WRONG - missing dependency
const handleAction = useCallback(async () => {
  await fetchData();
}, []);  // fetchData is missing
```

### 6. Modal Focus Management

The Modal component handles focus automatically. Just pass `isOpen` and `onClose`:

```tsx
<Modal
  isOpen={isModalOpen}
  onClose={() => setIsModalOpen(false)}
  title="Modal Title"
>
  <ModalContent />
</Modal>
```

### 7. Protected Routes

Wrap protected routes with `<ProtectedRoute />` element wrapper:

```tsx
<Route element={<ProtectedRoute />}>
  <Route path="/analytics" element={<AnalyticsPage />} />
  <Route path="/settings" element={<SettingsPage />} />
</Route>
```

## Before Implementing New Features

### Checklist

- [ ] Review [root CLAUDE.md](../CLAUDE.md) for project-wide conventions
- [ ] Review 2-3 similar existing implementations in this codebase
- [ ] Identify required types and add to `types/index.ts`
- [ ] Verify backend schema matches frontend types (API contract)
- [ ] Plan API endpoints (all URLs must have trailing slashes)
- [ ] Create custom hook if data fetching is involved
- [ ] Design component with proper accessibility attributes
- [ ] Add styles using CSS custom properties
- [ ] Handle loading, error, and empty states
- [ ] Add MSW handlers for testing
- [ ] Write component and integration tests
