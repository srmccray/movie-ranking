# Feature: Google Account Linking for Authenticated Users

## Overview

Enable users who are logged in with email/password accounts to link their Google account from a settings page. This allows users to use Google as an alternative login method after initially registering with email/password.

## Problem Statement

Currently, Google account linking only happens implicitly when a user logs in with Google and their email matches an existing account (handled in `google_auth.py` lines 337-342). However, users who:
1. Registered with email/password
2. Are currently logged in
3. Want to proactively add Google as a login method

...have no way to do this. They would have to log out and log back in via Google, which is not intuitive.

## Goals & Success Criteria

- [ ] Authenticated users can link their Google account from a Settings page
- [ ] The linking flow is secure (validates Google token, requires authenticated session)
- [ ] After linking, users can sign in with either email/password or Google
- [ ] Clear UI feedback during the linking process
- [ ] Proper error handling for edge cases (Google account already linked, etc.)

## User Stories

### US-1: Link Google Account from Settings

```
As a logged-in user with an email/password account,
I want to link my Google account from a settings page,
So that I can use Google as an alternative sign-in method.

Acceptance Criteria:
- Given I am logged in, when I navigate to Settings, then I see a "Link Google Account" button
- Given I click the button, when I complete Google OAuth, then my account is linked
- Given the linking succeeds, when I view Settings, then I see my linked Google account
- Given my account is already linked to Google, when I view Settings, then I see "Google account linked"

Definition of Done:
- [ ] Settings page exists and is accessible from navigation
- [ ] Link Google Account button initiates OAuth flow
- [ ] Backend validates the authenticated user before linking
- [ ] User sees success/error feedback after linking attempt
- [ ] Settings page shows linked status
```

### US-2: Error Handling During Linking

```
As a user attempting to link my Google account,
I want to see clear error messages when something goes wrong,
So that I understand what happened and how to proceed.

Acceptance Criteria:
- Given I try to link a Google account already linked to another user, when linking fails, then I see "This Google account is already linked to another account"
- Given the OAuth flow fails, when I return to the app, then I see a clear error message
- Given I cancel the OAuth flow, when I return to Settings, then I am not shown an error

Definition of Done:
- [ ] All error scenarios display user-friendly messages
- [ ] Errors do not expose sensitive information
- [ ] User can retry linking after errors
```

## Scope

### In Scope

1. **Backend**
   - New endpoint: `GET /api/v1/auth/google/link/` - Initiate linking flow for authenticated users
   - New endpoint: `GET /api/v1/auth/google/link/callback/` - Handle OAuth callback for linking
   - Store linking context in OAuthState (user_id being linked)
   - Validate that authenticated user matches the linking request

2. **Frontend**
   - New Settings page (`/settings`)
   - "Link Google Account" button component
   - Callback handling for linking flow
   - Display linked status
   - Navigation to Settings from Header

3. **Security**
   - Require authentication for linking endpoints
   - Validate user session throughout the flow
   - Prevent linking a Google account already linked elsewhere

### Out of Scope

- Unlinking Google accounts (future feature)
- Multiple Google accounts per user
- Other OAuth providers
- Profile picture/name from Google

## Technical Design

### Backend Changes

#### 1. Extend OAuthState Model

Add `user_id` field to track which user initiated the linking:

```python
# In app/models/oauth_state.py
user_id: Mapped[UUID | None] = mapped_column(
    ForeignKey("users.id", ondelete="CASCADE"),
    nullable=True,
)
flow_type: Mapped[str] = mapped_column(
    String(50),
    nullable=False,
    default="login",
    server_default=text("'login'"),
)
```

#### 2. New Endpoints in google_auth.py

```python
# GET /api/v1/auth/google/link/
# Requires: Authentication (CurrentUser dependency)
# Purpose: Initiate Google OAuth for account linking
# Returns: { authorization_url: string }

# GET /api/v1/auth/google/link/callback/
# Purpose: Handle OAuth callback specifically for linking
# Validates: OAuth state contains user_id, user is still authenticated
# Returns: Redirect to /settings?linked=success or /settings?error=...
```

#### 3. New Schema

```python
# In app/schemas/oauth.py
class GoogleLinkStatusResponse(BaseModel):
    """Response for checking Google link status."""
    is_linked: bool
    google_email: str | None = None  # Future: if we store Google email
```

#### 4. User Profile Endpoint (optional, for showing link status)

```python
# GET /api/v1/auth/me/
# Returns current user info including auth_provider
```

### Frontend Changes

#### 1. New Settings Page

Location: `/frontend/src/pages/SettingsPage.tsx`

Features:
- Display user email
- Show Google link status (based on auth_provider field)
- "Link Google Account" button (if not linked)
- "Google Account Linked" badge (if linked)

#### 2. API Client Methods

```typescript
// In api/client.ts
async getGoogleLinkUrl(): Promise<GoogleAuthUrlResponse> {
  return this.request<GoogleAuthUrlResponse>('/auth/google/link/');
}

async getCurrentUser(): Promise<UserResponse> {
  return this.request<UserResponse>('/auth/me/');
}
```

#### 3. Types

```typescript
// In types/index.ts
export interface UserResponse {
  id: string;
  email: string;
  auth_provider: 'local' | 'google' | 'linked';
  created_at: string;
}
```

#### 4. Routing

- Add `/settings` route (protected)
- Add `/auth/google/link/callback` route for linking callback

### Database Migration

```python
# alembic/versions/00X_add_oauth_state_user_id.py
# Add user_id and flow_type columns to oauth_states table
```

## API Contract

### GET /api/v1/auth/google/link/

**Purpose**: Initiate Google OAuth for account linking (authenticated users only)

**Request**: None (uses auth token)

**Response**:
```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?..."
}
```

**Errors**:
- `401` - Not authenticated
- `409` - User already has Google account linked
- `500` - Google OAuth not configured

### GET /api/v1/auth/google/link/callback/

**Purpose**: Handle OAuth callback for account linking

**Query Parameters**:
- `code`: Authorization code from Google
- `state`: CSRF state token
- `error`: Error from Google (if user denied)

**Response**: Redirect to `/settings?linked=success`

**Error Redirects**:
- `/settings?error=cancelled` - User cancelled OAuth
- `/settings?error=invalid_state` - Invalid/expired state
- `/settings?error=already_linked` - Google account linked to another user
- `/settings?error=failed` - Generic failure

### GET /api/v1/auth/me/

**Purpose**: Get current user profile

**Response**:
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "auth_provider": "local",
  "created_at": "2024-01-15T10:00:00Z"
}
```

## Edge Cases & Error Handling

| Edge Case | Backend Handling | Frontend Display |
|-----------|------------------|------------------|
| User cancels Google OAuth | Detect `error` param, redirect with `?error=cancelled` | "Google linking was cancelled" |
| Google account already linked to another user | Check google_id uniqueness, return 409 | "This Google account is already linked to another account" |
| OAuth state expired | Validate state, redirect with `?error=invalid_state` | "Session expired, please try again" |
| User's session expired during OAuth | Can't validate user_id in state, redirect with error | "Please log in again to link your Google account" |
| Google email doesn't match user's email | Allow linking anyway (they own both accounts) | Success - accounts linked |
| User already has Google linked | Check auth_provider, return 409 on /link/ initiation | Button disabled/hidden, show "Already linked" |

## Task Breakdown

### Phase 1: Backend (backend-engineer)

1. **Database Migration** - Add `user_id` and `flow_type` to OAuthState
2. **Schema Updates** - Add `GoogleLinkStatusResponse`, update `UserResponse`
3. **User Profile Endpoint** - `GET /api/v1/auth/me/`
4. **Link Initiation Endpoint** - `GET /api/v1/auth/google/link/`
5. **Link Callback Endpoint** - `GET /api/v1/auth/google/link/callback/`
6. **Tests** - Unit and integration tests for linking flow

### Phase 2: Frontend (frontend-react-engineer)

1. **Types** - Add `UserResponse` type, update `AuthContextType`
2. **API Client** - Add `getGoogleLinkUrl()` and `getCurrentUser()` methods
3. **Settings Page** - Create `/settings` page with link status
4. **Link Callback Page** - Handle `/auth/google/link/callback` route
5. **Navigation** - Add Settings link to Header
6. **Tests** - Component tests and MSW handlers

### Phase 3: QA (qa-test-engineer)

1. **E2E Testing** - Full linking flow test
2. **Error Scenario Testing** - All edge cases

## Dependencies

- Existing Google OAuth implementation (`app/routers/google_auth.py`)
- OAuthState model (`app/models/oauth_state.py`)
- User model with `google_id` and `auth_provider` fields
- Frontend AuthContext

## Timeline Estimate

- Backend: 2-3 hours
- Frontend: 2-3 hours
- Testing: 1 hour
- Total: 5-7 hours
