---
id: '0003'
title: Auto-Logout on 401 Unauthorized
status: Shipped
created: 2026-01-17
target_persona: Casey (The Movie Enthusiast)
component: auth
---

# PRD-0003 — Auto-Logout on 401 Unauthorized

## Who this is for

- **Casey (The Movie Enthusiast)**: Returns to the app with an expired or invalid token.

## What the person cannot do today

- Expired/invalid tokens cause API calls to fail with 401 and surface as confusing generic error messages instead of sending the user to log in.

## What good looks like

1. **Callback Injection**: `ApiClient.setOnUnauthorized()` registers a callback that `request()` invokes on any 401.
2. **AuthContext Wiring**: `AuthProvider` registers `logout` as the callback, clearing the token so `ProtectedRoute` redirects to `/login`.

## What this does not do

- Token refresh (not implemented; would precede logout if added later).
- Backend changes.

## Checkable Outcomes

1. When an API call returns 401, the user is automatically logged out
2. After logout, the user is redirected to the login page (handled by existing ProtectedRoute)
3. The token is removed from localStorage on 401
4. Failed login/register attempts (which return 401) still show appropriate error messages
5. Existing tests continue to pass
6. No infinite loops or race condition issues with multiple 401 responses

## Linked User Stories

- `US-0003`

## Implementing Backlog Tasks

- Implemented directly (SMALL tier, no task breakdown).

## Shipped Evidence

- Shipped in commit `1883317` (2026-01-17, "Add auto-logout on 401 and fix spinner animation"): `setOnUnauthorized()` in `frontend/src/api/client.ts` (invoked on a 401 in both `request()` and the multipart import upload), registered with `logout` in a `useEffect` in `frontend/src/context/AuthContext.tsx` and cleared on unmount.
- Test coverage note: no automated test exercises `setOnUnauthorized()` or the 401 -> logout redirect directly. Outcome 4 is supported by `frontend/src/api/client.test.ts` (a failed login still rejects with an `ApiClientError` of status 401) and by the code path (the callback only clears the token, then the error is still thrown). Outcome 6 (no loops/races) is a code-review claim: `logout` is idempotent and `setOnUnauthorized` is registered once per `logout` identity.

## Legacy Specification

_Migrated verbatim (headings demoted) from the legacy `.claude_docs/` tree on 2026-10-13._

_Historical design record: code samples and statuses below reflect the plan at the time (2026-01-17) and may differ from the shipped code; the sections above are authoritative. The `.claude_docs/` tree was removed in commit `fb641e6` and remains available in git history before that commit._

### Source: `.claude_docs/features/auto-logout-on-401/sketch.md`

### Quick Sketch: Auto-Logout on 401 Unauthorized

**Created:** 2026-01-17
**Tier:** SMALL
**Triage Scores:** Complexity 3/10, Risk 2/10

#### What

Add automatic logout when API calls return 401 unauthorized errors. When a user returns to the app with an expired or invalid token, instead of showing generic error messages, automatically log them out and redirect to the login page.

#### Why

Currently, when a user's token expires or becomes invalid, API calls fail with 401 errors that display as generic error messages. This creates a confusing user experience. Users should be seamlessly redirected to login so they can re-authenticate without encountering cryptic error states.

#### Approach

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

#### Files Likely Affected

- `/Users/stephen/Projects/movie-ranking/frontend/src/api/client.ts` - Add `onUnauthorized` callback property and `setOnUnauthorized()` method; modify `request()` to check 401 and invoke callback
- `/Users/stephen/Projects/movie-ranking/frontend/src/context/AuthContext.tsx` - Register `logout` as the unauthorized callback during initialization

#### Considerations

- **Auth endpoints exemption**: The login/register endpoints should NOT trigger auto-logout on 401 (a failed login is expected). Since these endpoints are called before the user is authenticated, the callback will clear a null token anyway - no harm done. However, if needed, we could add an `options.skipUnauthorizedCallback` parameter.
- **Race conditions**: Multiple simultaneous API calls might all fail with 401 and trigger logout multiple times. The logout function is idempotent (clearing localStorage twice is fine), so this is safe.
- **Token refresh**: This project does not currently implement token refresh. If added later, the 401 handler should attempt refresh before triggering logout.
- **Testing**: MSW handlers in tests should continue to work. The callback will be null unless explicitly set in tests.

#### Implementation Details

##### ApiClient Changes

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

##### AuthContext Changes

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

#### Acceptance Criteria

- [ ] When an API call returns 401, the user is automatically logged out
- [ ] After logout, the user is redirected to the login page (handled by existing ProtectedRoute)
- [ ] The token is removed from localStorage on 401
- [ ] Failed login/register attempts (which return 401) still show appropriate error messages
- [ ] Existing tests continue to pass
- [ ] No infinite loops or race condition issues with multiple 401 responses

---

#### Next Agent to Invoke

**Agent:** `frontend-implementation`

**Context to provide:**
- Feature slug: `auto-logout-on-401`
- Tier: SMALL
- Sketch location: `/Users/stephen/Projects/movie-ranking/.claude_docs/features/auto-logout-on-401/sketch.md`
- Implementation is straightforward - modify two files as outlined in the sketch
- No backend changes required

**After that agent completes:**
The feature should be fully implemented with the callback injection pattern connecting ApiClient to AuthContext for 401 handling.
