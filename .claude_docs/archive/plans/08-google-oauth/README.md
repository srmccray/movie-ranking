# Feature: Google OAuth Login

## Overview

Add Google OAuth 2.0 authentication as an alternative login method to the Movie Ranking application. Users will be able to sign in with their Google account in addition to the existing email/password authentication, providing a faster and more convenient login experience while maintaining security.

## Problem Statement

Currently, users must create a dedicated account with email and password to use the Movie Ranking app. This creates friction in the onboarding process:
- Users must remember yet another password
- Email verification adds steps to the signup flow
- Password reset flows require additional infrastructure
- Some users prefer social login for convenience and trust

By adding Google OAuth, we reduce friction for users who prefer social authentication while maintaining the existing email/password option for those who prefer it.

## Goals & Success Criteria

- [ ] Users can sign up/sign in using their Google account with a single click
- [ ] Existing email/password authentication continues to work unchanged
- [ ] Users with existing accounts (same email) can link their Google account
- [ ] Google OAuth tokens are securely validated server-side
- [ ] User experience is seamless with clear feedback during the auth flow
- [ ] No security vulnerabilities introduced (CSRF protection, token validation)

## User Stories

### US-1: Sign Up with Google

```
As a new user,
I want to sign up using my Google account,
So that I can start using the app quickly without creating a new password.

Acceptance Criteria:
- Given I am on the login page, when I click "Sign in with Google", then I am redirected to Google's OAuth consent screen
- Given I authorize the app on Google, when I am redirected back, then a new account is created with my Google email
- Given the account is created, when the flow completes, then I am logged in and redirected to the rankings page
- Given I already have an account with this email, when I try to sign up with Google, then my accounts are linked (see US-3)

Definition of Done:
- [ ] Google Sign-In button is visible on login and register pages
- [ ] OAuth flow redirects to Google and back successfully
- [ ] New user record is created in database with Google provider info
- [ ] JWT token is issued after successful authentication
- [ ] User lands on rankings page after successful auth
```

### US-2: Sign In with Google (Returning User)

```
As a returning user who signed up with Google,
I want to sign in using my Google account,
So that I can access my rankings without typing a password.

Acceptance Criteria:
- Given I previously signed up with Google, when I click "Sign in with Google", then I am authenticated with my existing account
- Given I am authenticated, when the flow completes, then my existing rankings are accessible
- Given my Google session is active, when I authorize, then the process is quick (no re-entering credentials)

Definition of Done:
- [ ] Returning Google users are recognized by email
- [ ] User's existing data (rankings, preferences) is preserved
- [ ] Authentication is seamless for users with active Google sessions
```

### US-3: Account Linking (Existing Email Account)

```
As a user who registered with email/password,
I want to link my Google account,
So that I can use either method to sign in.

Acceptance Criteria:
- Given I have an email/password account, when I click "Sign in with Google" with the same email, then I am prompted to link accounts
- Given I confirm account linking, when the link is complete, then I can use both authentication methods
- Given I deny account linking, when I return to the app, then I can still use my email/password to sign in

Definition of Done:
- [ ] System detects when Google email matches existing account
- [ ] User is informed about account linking option
- [ ] After linking, both auth methods work for the same account
- [ ] User data is not duplicated or lost during linking
```

### US-4: Error Handling

```
As a user,
I want clear feedback when Google authentication fails,
So that I know what went wrong and how to proceed.

Acceptance Criteria:
- Given Google authentication fails, when I return to the app, then I see a clear error message
- Given I cancel the Google auth flow, when I return to the app, then I am on the login page without error
- Given the OAuth token is invalid, when validation fails, then I am prompted to try again
- Given there is a network error, when the flow fails, then I see a helpful error message

Definition of Done:
- [ ] All error scenarios display user-friendly messages
- [ ] Users can retry authentication after errors
- [ ] No sensitive error details are exposed to users
- [ ] Errors are logged server-side for debugging
```

## Scope

### In Scope

1. **Backend OAuth Implementation**
   - Google OAuth 2.0 flow with authorization code exchange
   - Server-side ID token validation using Google's public keys
   - New user creation from Google profile data
   - Account linking for existing email accounts
   - New database fields for OAuth provider information
   - CSRF state parameter protection

2. **Frontend Integration**
   - Google Sign-In button on Login and Register pages
   - OAuth redirect handling
   - Loading states during OAuth flow
   - Error display for failed authentication
   - AuthContext updates for Google login

3. **Security Measures**
   - CSRF protection via state parameter
   - Server-side token validation (not client-side)
   - Secure storage of OAuth tokens
   - No exposure of client secrets to frontend

4. **User Experience**
   - Seamless redirect flow (no popup)
   - Clear visual feedback during authentication
   - Consistent design with existing auth UI

### Out of Scope

1. **Other OAuth Providers** - Apple, GitHub, Facebook, etc. (future feature)
2. **Account Unlinking** - Users cannot disconnect Google from their account (future feature)
3. **Google API Access** - No access to Google Drive, Calendar, etc.
4. **Two-Factor Authentication** - 2FA is out of scope
5. **Password-less Migration** - Users who linked Google can still use password

## User Experience

### Login Flow

1. User navigates to `/login`
2. User sees existing email/password form AND a "Sign in with Google" button
3. User clicks Google button
4. User is redirected to Google's OAuth consent screen
5. User authorizes the application
6. User is redirected back to `/auth/google/callback`
7. Backend validates the token and creates/finds the user
8. Frontend receives JWT and redirects to rankings page

### Register Flow

1. User navigates to `/register`
2. User sees existing registration form AND a "Sign up with Google" button
3. Flow continues same as login (new account created if needed)

### Account Linking Flow

1. User with email/password account clicks "Sign in with Google"
2. Google email matches existing account
3. Backend automatically links accounts (same user, adds Google provider)
4. User is logged in to their existing account

### Visual Design

- Google button follows Google's branding guidelines
- Button placement: Below the form, separated by an "or" divider
- Consistent styling with existing buttons (sizing, spacing)

## Data Requirements

### New Database Fields (User Model)

```python
# Add to User model
google_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
auth_provider: Mapped[str] = mapped_column(String(50), default="local")  # "local" | "google" | "linked"
```

### OAuth State Storage

```python
# Temporary state storage (Redis or database table)
# For CSRF protection during OAuth flow
oauth_state: {
    state: str (random token)
    created_at: datetime
    redirect_uri: str
    expires_at: datetime (5 minutes)
}
```

### Google Profile Data Used

- `sub`: Google user ID (stored as `google_id`)
- `email`: User's email address
- `email_verified`: Must be true
- `name`: Display name (optional, for future use)
- `picture`: Profile picture URL (optional, for future use)

## API Requirements

### GET /api/v1/auth/google/login/

**Purpose**: Initiate Google OAuth flow by returning the authorization URL

```
Request: (none - just GET request)

Response: {
    authorization_url: string - Full Google OAuth URL with state
}

Edge Cases:
- Missing Google client ID in config -> 500 with generic error
```

### GET /api/v1/auth/google/callback/

**Purpose**: Handle OAuth callback from Google

```
Request: (query parameters from Google redirect)
    code: string (required) - Authorization code from Google
    state: string (required) - CSRF state token
    error: string (optional) - Error from Google if user denied

Response (success): {
    access_token: string - JWT token for the user
    token_type: "bearer"
}

Response (account linking needed): {
    requires_linking: true
    email: string
    message: "Account with this email exists. Sign in with password to link."
}

Edge Cases:
- Invalid/expired state token -> 400 "Invalid authentication state"
- User denied OAuth -> 400 "Authentication cancelled"
- Invalid authorization code -> 400 "Invalid authorization code"
- Email not verified on Google -> 400 "Email not verified"
- Server error exchanging token -> 500 "Authentication failed"
```

### POST /api/v1/auth/google/link/

**Purpose**: Link Google account to existing email/password account

```
Request: {
    google_id_token: string - ID token from Google
    password: string - Current password to verify ownership
}

Response (success): {
    access_token: string - New JWT token
    message: "Google account linked successfully"
}

Edge Cases:
- Wrong password -> 401 "Invalid password"
- Google account already linked to another user -> 409 "Google account already linked"
- No account with this email -> 404 "Account not found"
```

## Edge Cases & Error Handling

| Edge Case | Handling |
|-----------|----------|
| User cancels on Google consent screen | Show friendly message, return to login page |
| Google email already exists as local account | Auto-link accounts if email verified, or prompt for password |
| OAuth state token expired (user took too long) | Show error, provide "Try again" button |
| Google ID token validation fails | Log error, show generic "Authentication failed" message |
| User's Google email is not verified | Reject auth, show "Please verify your Google email" |
| Network error during token exchange | Show error with retry option |
| Google returns an error | Parse error type, show appropriate message |
| User has multiple Google accounts | Google handles account selection |
| Rate limiting from Google | Respect rate limits, queue retries |
| Existing google_id links to different email | Edge case - shouldn't happen if we validate properly |

## Security Considerations

1. **State Parameter (CSRF Protection)**
   - Generate cryptographically random state on `/google/login/`
   - Store state in session/database with expiration
   - Validate state on callback before exchanging code

2. **Token Validation**
   - Validate ID token signature using Google's public keys
   - Verify `aud` claim matches our client ID
   - Verify `iss` claim is Google
   - Check `exp` claim is not expired
   - Verify `email_verified` is true

3. **No Client Secret Exposure**
   - Client secret only used server-side
   - Never include in frontend code or responses

4. **HTTPS Only**
   - OAuth redirect URIs must use HTTPS in production

5. **Token Storage**
   - JWT returned to frontend, stored in localStorage (same as current)
   - No refresh tokens stored (rely on JWT expiration)

## Configuration Requirements

### Environment Variables

```bash
# Add to .env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback/  # or production URL
```

### Google Cloud Console Setup

1. Create OAuth 2.0 credentials in Google Cloud Console
2. Configure authorized redirect URIs
3. Add authorized JavaScript origins for frontend
4. Enable Google+ API (or People API) if needed

## Dependencies

### External Dependencies
- Google Cloud Platform account with OAuth 2.0 credentials
- `google-auth` Python library for token validation
- `httpx` for async HTTP requests to Google

### Internal Dependencies
- Existing User model (will be extended)
- Existing auth router (will add new endpoints)
- Existing AuthContext (will add Google login method)
- JWT token generation (existing `create_access_token`)

## Open Questions

- [ ] Should we store Google refresh tokens for future API access, or just use OAuth for authentication only?
  - **Recommendation**: Authentication only (no refresh tokens) - simpler and matches current JWT-only approach

- [ ] Should account linking require password confirmation, or auto-link if emails match?
  - **Recommendation**: Auto-link if email is verified on Google (secure and frictionless)

- [ ] Should we use popup or redirect flow for OAuth?
  - **Recommendation**: Redirect flow (simpler, better mobile support, no popup blockers)

- [ ] What happens if a user tries to register with email/password using a Google-linked email?
  - **Recommendation**: Allow it - they can use either method (auth_provider becomes "linked")

## Technical Notes for Implementation

### Recommended Libraries

```python
# requirements.txt additions
google-auth>=2.0.0
google-auth-oauthlib>=1.0.0
```

### Token Validation Pattern

```python
from google.oauth2 import id_token
from google.auth.transport import requests

def verify_google_token(token: str) -> dict:
    """Verify Google ID token and return claims."""
    idinfo = id_token.verify_oauth2_token(
        token,
        requests.Request(),
        settings.GOOGLE_CLIENT_ID
    )
    return idinfo
```

### Frontend Google Button

Consider using Google's official button or a styled custom button that follows Google's branding guidelines.
