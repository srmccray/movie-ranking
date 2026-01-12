# Frontend Development Guide

This document provides comprehensive guidance for developing features in the Movie Ranking frontend application.

## Project Overview

A React + TypeScript frontend built with Vite, featuring:
- React Router for navigation
- Context API for authentication state
- Custom hooks for data fetching
- CSS custom properties for theming
- MSW for API mocking in tests

## Project Structure

```
frontend/src/
├── api/
│   └── client.ts          # API client singleton with typed methods
├── components/
│   ├── index.ts           # Barrel exports for all components
│   ├── Button.tsx         # Reusable button with variants
│   ├── Input.tsx          # Form input with label and error handling
│   ├── Modal.tsx          # Accessible modal dialog
│   ├── Header.tsx         # App header with auth state
│   ├── StarRating.tsx     # Interactive star rating component
│   ├── MovieCard.tsx      # Movie display with actions
│   ├── EmptyState.tsx     # Empty state placeholder
│   ├── AddMovieForm.tsx   # Form for adding movies
│   └── ProtectedRoute.tsx # Auth route wrapper
├── context/
│   └── AuthContext.tsx    # Authentication provider and hook
├── hooks/
│   └── useRankings.ts     # Rankings data hook with CRUD operations
├── pages/
│   ├── LoginPage.tsx      # Login form page
│   ├── RegisterPage.tsx   # Registration form page
│   └── RankingsPage.tsx   # Main rankings display page
├── types/
│   └── index.ts           # All TypeScript interfaces
├── __tests__/
│   ├── setup.ts           # Vitest setup with MSW
│   └── mocks/
│       ├── handlers.ts    # MSW request handlers
│       └── server.ts      # MSW server instance
├── App.tsx                # Root component with routing
├── main.tsx               # Application entry point
└── index.css              # Global styles and design tokens
```

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

### 3. Add Component Styles

Add to `/frontend/src/index.css`:

```css
/* New Component */
.new-component {
  background-color: var(--color-bg-primary);
  border: 1px solid var(--color-neutral-200);
  border-radius: var(--radius-xl);
  padding: var(--space-4);
}

.new-component-highlighted {
  border-color: var(--color-primary-500);
}

.new-component-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--color-neutral-900);
  margin-bottom: var(--space-2);
}

.new-component-content {
  color: var(--color-neutral-600);
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

For components wrapping HTML elements, extend native attributes:

```tsx
import type { ButtonHTMLAttributes, ReactNode } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost';
  loading?: boolean;
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

          {/* Protected routes */}
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<RankingsPage />} />
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

  // New Item endpoints - NOTE TRAILING SLASHES!
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

### CRITICAL: Trailing Slashes

**All API endpoints MUST include trailing slashes.** FastAPI will 307 redirect without them, causing CORS and authentication issues.

```tsx
// CORRECT
await this.request<Item>('/items/');
await this.request<Item>(`/items/${id}/`);
await this.request<ItemList>(`/items/?limit=${limit}`);

// WRONG - will cause 404 or redirect errors
await this.request<Item>('/items');
await this.request<Item>(`/items/${id}`);
```

### Content-Type Rules

- **JSON requests** (default): Automatically set to `application/json`
- **Form data** (login only): Use `application/x-www-form-urlencoded`
- **Delete requests**: No Content-Type needed (no body)

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

### Handling 204 No Content

The API client already handles 204 responses:

```tsx
// In client.ts request method
if (response.status === 204) {
  return undefined as T;
}
```

## API Contract Verification

### The Problem

Frontend-backend type mismatches cause runtime errors that are not caught during development or by TypeScript compilation. For example:
- Backend returns `{ results: T[], query: string }`
- Frontend expects `T[]` directly
- TypeScript compiles successfully, but crashes at runtime

### Before Implementing Any API Integration

**Checklist:**

- [ ] **Read the backend schema file** for the endpoint (`app/schemas/<entity>.py`)
- [ ] **Read the backend router file** to see the `response_model=` declaration
- [ ] **Verify the exact response shape** - is it a wrapper object or raw data?
- [ ] **Check for nested types** - wrapper responses often contain `items`, `results`, `data`, etc.
- [ ] **Add all required types to `types/index.ts`** including wrapper/response types
- [ ] **Match field names exactly** - backend uses `snake_case`, frontend types must match

### Response Shape Patterns

The backend uses these common response patterns:

| Pattern | Backend Schema | Frontend Type Needed |
|---------|---------------|---------------------|
| Single item | `EntityResponse` | `Entity` |
| List with pagination | `EntityListResponse` | `{ items: Entity[], total, limit, offset }` |
| Search results | `TMDBSearchResponse` | `{ results: TMDBSearchResult[], query, year }` |
| Delete | `204 No Content` | `void` |

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

### Common Mistakes to Avoid

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

3. **Mismatched field names**
   ```typescript
   // Backend returns: { "tmdb_id": 12345 }

   // WRONG
   interface Movie { tmdbId: number; }

   // CORRECT - match snake_case from backend
   interface Movie { tmdb_id: number; }
   ```

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

### Verification Commands

Before implementing, verify the contract:

```bash
# View backend response schema
cat app/schemas/movie.py

# View endpoint response_model
grep -A 5 "def search" app/routers/movies.py

# Test endpoint directly (requires auth token)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/movies/search/?q=test
```

## Adding New Types

### Type Organization

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

## Styling Conventions

### Design Tokens

All styling uses CSS custom properties defined in `/frontend/src/index.css`:

```css
:root {
  /* Colors */
  --color-primary-500: #3b82f6;
  --color-primary-600: #2563eb;
  --color-neutral-500: #64748b;
  --color-error: #ef4444;
  --color-star-filled: #fbbf24;

  /* Spacing (4px base) */
  --space-1: 0.25rem;   /* 4px */
  --space-2: 0.5rem;    /* 8px */
  --space-3: 0.75rem;   /* 12px */
  --space-4: 1rem;      /* 16px */
  --space-6: 1.5rem;    /* 24px */
  --space-8: 2rem;      /* 32px */

  /* Border Radius */
  --radius-sm: 0.25rem;
  --radius-md: 0.375rem;
  --radius-lg: 0.5rem;
  --radius-xl: 0.75rem;

  /* Shadows */
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);
}
```

### Style Patterns

**Always use CSS custom properties:**

```css
/* CORRECT */
.component {
  padding: var(--space-4);
  color: var(--color-neutral-700);
  border-radius: var(--radius-lg);
}

/* WRONG - hardcoded values */
.component {
  padding: 16px;
  color: #334155;
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
```

### Adding New Styles

Add styles to `/frontend/src/index.css` following existing patterns:

```css
/* New Feature Component */
.new-feature {
  /* Use existing tokens */
  background-color: var(--color-bg-primary);
  border: 1px solid var(--color-neutral-200);
  border-radius: var(--radius-xl);
  padding: var(--space-4);
  box-shadow: var(--shadow-sm);
}

.new-feature:hover {
  border-color: var(--color-neutral-300);
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
  const { isAuthenticated, isLoading, login, logout, register } = useAuth();

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }

  return <AuthenticatedContent />;
}
```

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
    fetchRankings, // Fetch/refresh function
    loadMore,      // Pagination function
    addMovieAndRank,
    updateRating,
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

Place tests next to the file being tested:

```
components/
  Button.tsx
  Button.test.tsx  # or in __tests__ folder
```

Or in the `__tests__` folder for integration tests.

### MSW Mock Handlers

Add handlers in `/frontend/src/__tests__/mocks/handlers.ts`:

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

### 1. Trailing Slashes on API Calls

**CRITICAL**: All API endpoints require trailing slashes.

```tsx
// CORRECT
'/api/v1/rankings/'
'/api/v1/rankings/?limit=20'
`/api/v1/rankings/${id}/`

// WRONG - causes 404 or redirect errors
'/api/v1/rankings'
`/api/v1/rankings/${id}`
```

### 2. Date Handling

Send dates as ISO 8601 UTC strings:

```tsx
// CORRECT
const ratedAt = new Date().toISOString();  // "2024-01-15T10:30:00.000Z"

// For date inputs, convert local date to ISO
const localDate = '2024-01-15';  // from <input type="date">
const isoDate = new Date(localDate).toISOString();
```

### 3. Login Content-Type

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

### 4. Component Imports

Always import from barrel file when available:

```tsx
// CORRECT
import { Button, Input, Modal } from '../components';

// AVOID
import { Button } from '../components/Button';
import { Input } from '../components/Input';
```

### 5. Form Event Handling

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

### 6. useCallback Dependencies

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

### 7. Modal Focus Management

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

### 8. Protected Routes

Wrap protected routes with `<ProtectedRoute />` element wrapper:

```tsx
<Route element={<ProtectedRoute />}>
  <Route path="/dashboard" element={<DashboardPage />} />
  <Route path="/settings" element={<SettingsPage />} />
</Route>
```

## Before Implementing New Features

### Checklist

- [ ] Review 2-3 similar existing implementations
- [ ] Identify required types and add to `types/index.ts`
- [ ] Plan API endpoints with trailing slashes
- [ ] Create custom hook if data fetching is involved
- [ ] Design component with proper accessibility attributes
- [ ] Add styles using CSS custom properties
- [ ] Handle loading, error, and empty states
- [ ] Add MSW handlers for testing
- [ ] Write component and integration tests
