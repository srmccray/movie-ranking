# Quick Sketch: Auto-Logout on 401 Unauthorized

**Created:** 2026-01-17
**Tier:** SMALL
**Triage Scores:** Complexity 3/10, Risk 2/10

## What

Add automatic logout when API calls return 401 unauthorized errors. When a user returns to the app with an expired or invalid token, instead of showing generic error messages, automatically log them out and redirect to the login page.

## Why

Currently, when a user's token expires or becomes invalid, API calls fail with 401 errors that display as generic error messages. This creates a confusing user experience. Users should be seamlessly redirected to login so they can re-authenticate without encountering cryptic error states.

## Approach

The `ApiClient` is a singleton class (not a React component), so it cannot directly access React context. The solution uses a callback injection pattern:

1. **Add callback registration to ApiClient** (`/Users/stephen/Projects/movie-ranking/frontend/src/api/client.ts`):
   - Add private property: `private onUnauthorized: (() => void) | null = null`
   - Add public method: `setOnUnauthorized(callback: (() => void) | null)`
   - In `request()` method, check for 401 status and call the callback before throwing

2. **Register logout callback in AuthContext** (`/Users/stephen/Projects/movie-ranking/frontend/src/context/AuthContext.tsx`):
   - In the initialization `useEffect`, call `apiClient.setOnUnauthorized(logout)`
   - Cleanup: set to `null` on unmount (though AuthProvider typically never unmounts)

3. **Handle the 401 in request method**:
   - Before throwing `ApiClientError` for 401, invoke `this.onUnauthorized?.()`
   - This triggers logout which clears token, updates state, and React Router will redirect to `/login`

## Files Likely Affected

- `/Users/stephen/Projects/movie-ranking/frontend/src/api/client.ts` - Add `onUnauthorized` callback property and `setOnUnauthorized()` method; modify `request()` to check 401 and invoke callback
- `/Users/stephen/Projects/movie-ranking/frontend/src/context/AuthContext.tsx` - Register `logout` as the unauthorized callback during initialization

## Considerations

- **Auth endpoints exemption**: The login/register endpoints should NOT trigger auto-logout on 401 (a failed login is expected). Since these endpoints are called before the user is authenticated, the callback will clear a null token anyway - no harm done. However, if needed, we could add an `options.skipUnauthorizedCallback` parameter.
- **Race conditions**: Multiple simultaneous API calls might all fail with 401 and trigger logout multiple times. The logout function is idempotent (clearing localStorage twice is fine), so this is safe.
- **Token refresh**: This project does not currently implement token refresh. If added later, the 401 handler should attempt refresh before triggering logout.
- **Testing**: MSW handlers in tests should continue to work. The callback will be null unless explicitly set in tests.

## Implementation Details

### ApiClient Changes

```typescript
// In client.ts
class ApiClient {
  private token: string | null = null;
  private onUnauthorized: (() => void) | null = null;

  setToken(token: string | null) {
    this.token = token;
  }

  setOnUnauthorized(callback: (() => void) | null) {
    this.onUnauthorized = callback;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    // ... existing header setup ...

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      // Handle 401 Unauthorized - trigger logout callback
      if (response.status === 401 && this.onUnauthorized) {
        this.onUnauthorized();
      }

      const error: ApiError = await response.json();
      throw new ApiClientError(response.status, error);
    }

    // ... rest of method ...
  }
}
```

### AuthContext Changes

```typescript
// In AuthContext.tsx
export function AuthProvider({ children }: { children: ReactNode }) {
  // ... existing state ...

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    apiClient.setToken(null);
  }, []);

  // Initialize auth state from localStorage
  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_KEY);
    if (storedToken) {
      setToken(storedToken);
      apiClient.setToken(storedToken);
    }

    // Register logout as the unauthorized callback
    apiClient.setOnUnauthorized(logout);

    setIsLoading(false);

    // Cleanup on unmount (though AuthProvider rarely unmounts)
    return () => {
      apiClient.setOnUnauthorized(null);
    };
  }, [logout]);

  // ... rest of component ...
}
```

## Acceptance Criteria

- [ ] When an API call returns 401, the user is automatically logged out
- [ ] After logout, the user is redirected to the login page (handled by existing ProtectedRoute)
- [ ] The token is removed from localStorage on 401
- [ ] Failed login/register attempts (which return 401) still show appropriate error messages
- [ ] Existing tests continue to pass
- [ ] No infinite loops or race condition issues with multiple 401 responses

---

## Next Agent to Invoke

**Agent:** `frontend-implementation`

**Context to provide:**
- Feature slug: `auto-logout-on-401`
- Tier: SMALL
- Sketch location: `/Users/stephen/Projects/movie-ranking/.claude_docs/features/auto-logout-on-401/sketch.md`
- Implementation is straightforward - modify two files as outlined in the sketch
- No backend changes required

**After that agent completes:**
The feature should be fully implemented with the callback injection pattern connecting ApiClient to AuthContext for 401 handling.
