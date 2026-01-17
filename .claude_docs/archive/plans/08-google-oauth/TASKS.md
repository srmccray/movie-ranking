# Google OAuth Implementation Tasks

## Overview

This document breaks down the Google OAuth feature into discrete tasks with agent assignments and dependencies. Tasks must be executed in the order specified, waiting for each to complete before proceeding to the next.

## Task Execution Order

```
Task 1 (backend-engineer): Database & Config
    |
    v
Task 2 (backend-engineer): OAuth Endpoints
    |
    v
Task 3 (frontend-react-engineer): Google Sign-In UI
    |
    v
Task 4 (frontend-react-engineer): OAuth Flow Integration
    |
    v
Task 5 (qa-test-engineer): Backend Tests
    |
    v
Task 6 (qa-test-engineer): Frontend Tests
    |
    v
Task 7 (devops-platform-engineer): Environment & Docs
```

---

## Task 1: Database Schema & Configuration

**Agent**: `backend-engineer`
**Priority**: P0 (Blocker)
**Estimated Effort**: Small

### Description

Extend the User model to support Google OAuth and add configuration settings for Google OAuth credentials.

### Deliverables

1. **Update User Model** (`app/models/user.py`)
   - Add `google_id: Mapped[str | None]` - unique Google user ID
   - Add `auth_provider: Mapped[str]` - "local", "google", or "linked"
   - Add unique index on `google_id`
   - Make `hashed_password` nullable (Google-only users don't have one)

2. **Create Migration** (`alembic/versions/NNN_add_google_oauth_fields.py`)
   - Add `google_id` column (String(255), unique, nullable)
   - Add `auth_provider` column (String(50), default "local")
   - Update `hashed_password` to be nullable

3. **Update Config** (`app/config.py`)
   - Add `GOOGLE_CLIENT_ID: str`
   - Add `GOOGLE_CLIENT_SECRET: str`
   - Add `GOOGLE_REDIRECT_URI: str`

4. **Update `.env.example`**
   - Add placeholder values for Google OAuth credentials

### Acceptance Criteria

- [ ] Migration runs successfully
- [ ] User model has google_id and auth_provider fields
- [ ] Config loads Google OAuth settings from environment
- [ ] Existing users have auth_provider="local" after migration

### Technical Notes

- Follow existing migration patterns in `alembic/versions/`
- Use nullable for google_id and hashed_password
- Default auth_provider to "local" for existing users

---

## Task 2: OAuth Endpoints Implementation

**Agent**: `backend-engineer`
**Priority**: P0 (Blocker)
**Dependencies**: Task 1
**Estimated Effort**: Medium

### Description

Implement the Google OAuth endpoints for initiating auth, handling callbacks, and linking accounts.

### Deliverables

1. **Create OAuth Schemas** (`app/schemas/oauth.py`)
   ```python
   class GoogleAuthResponse(BaseModel):
       authorization_url: str

   class GoogleCallbackRequest(BaseModel):
       code: str
       state: str

   class AccountLinkingResponse(BaseModel):
       requires_linking: bool
       email: str
       message: str
   ```

2. **Create OAuth Router** (`app/routers/google_auth.py`)

   **GET /api/v1/auth/google/login/**
   - Generate cryptographic state token
   - Store state in database/cache (with 5-minute expiry)
   - Return Google authorization URL with state

   **GET /api/v1/auth/google/callback/**
   - Validate state parameter (CSRF protection)
   - Exchange authorization code for tokens
   - Validate ID token using google-auth library
   - Find or create user by google_id or email
   - Handle account linking if email exists
   - Return JWT token

   **POST /api/v1/auth/google/link/** (optional)
   - Verify password for existing account
   - Link Google account to existing user

3. **Create OAuth State Model** (`app/models/oauth_state.py`)
   - Store state tokens with expiration
   - Or use simple in-memory cache if acceptable

4. **Register Router** (`app/main.py`)
   - Add google_auth router with prefix `/api/v1/auth/google`

5. **Add Dependencies** (`requirements.txt`)
   ```
   google-auth>=2.0.0
   google-auth-oauthlib>=1.0.0
   ```

### Acceptance Criteria

- [ ] /auth/google/login/ returns valid Google authorization URL
- [ ] /auth/google/callback/ exchanges code and returns JWT
- [ ] State token validation prevents CSRF attacks
- [ ] New users are created with auth_provider="google"
- [ ] Existing email users are linked with auth_provider="linked"
- [ ] Invalid states/codes return appropriate errors
- [ ] All endpoints follow trailing slash convention

### Technical Notes

- Use `google.oauth2.id_token.verify_oauth2_token()` for validation
- Store state in database table or use itsdangerous for signed tokens
- Match existing auth router patterns (status codes, error handling)
- ID token validation must check: aud, iss, exp, email_verified

### Security Checklist

- [ ] State parameter is cryptographically random
- [ ] State expires after 5 minutes
- [ ] ID token signature is verified
- [ ] Email must be verified on Google
- [ ] No client secret exposed to frontend

---

## Task 3: Google Sign-In Button Component

**Agent**: `frontend-react-engineer`
**Priority**: P0 (Blocker)
**Dependencies**: Task 2
**Estimated Effort**: Small

### Description

Create the Google Sign-In button component and integrate it into the login and register pages.

### Deliverables

1. **Create GoogleSignInButton Component** (`frontend/src/components/GoogleSignInButton.tsx`)
   - Follow Google branding guidelines
   - Include Google logo (SVG)
   - Support loading and disabled states
   - Consistent sizing with existing buttons

2. **Update Login Page** (`frontend/src/pages/LoginPage.tsx`)
   - Add divider with "or"
   - Add GoogleSignInButton below the form
   - Handle click to initiate OAuth flow

3. **Update Register Page** (`frontend/src/pages/RegisterPage.tsx`)
   - Same structure as login page
   - Button text: "Sign up with Google"

4. **Add Styles** (`frontend/src/index.css`)
   - Google button styling (white background, Google colors)
   - Divider styling for "or" separator
   - Hover and active states

5. **Export Component** (`frontend/src/components/index.ts`)
   - Add GoogleSignInButton to barrel export

### Acceptance Criteria

- [ ] Button matches Google branding guidelines
- [ ] Button appears on both login and register pages
- [ ] Button is clearly separated from email/password form
- [ ] Loading state shows spinner
- [ ] Component is accessible (aria-label, keyboard navigation)

### Design Reference

- White button with Google 'G' logo
- Text: "Sign in with Google" / "Sign up with Google"
- Border: 1px solid neutral-300
- Hover: subtle shadow/border change

---

## Task 4: OAuth Flow Integration

**Agent**: `frontend-react-engineer`
**Priority**: P0 (Blocker)
**Dependencies**: Task 3
**Estimated Effort**: Medium

### Description

Integrate the full OAuth flow including redirect handling, callback processing, and AuthContext updates.

### Deliverables

1. **Add API Methods** (`frontend/src/api/client.ts`)
   ```typescript
   async getGoogleAuthUrl(): Promise<{ authorization_url: string }> {
     return this.request('/auth/google/login/');
   }

   async handleGoogleCallback(code: string, state: string): Promise<Token> {
     return this.request(`/auth/google/callback/?code=${code}&state=${state}`);
   }
   ```

2. **Add Types** (`frontend/src/types/index.ts`)
   ```typescript
   interface GoogleAuthUrlResponse {
     authorization_url: string;
   }

   interface GoogleCallbackResponse {
     access_token: string;
     token_type: string;
   }

   interface AccountLinkingRequired {
     requires_linking: boolean;
     email: string;
     message: string;
   }
   ```

3. **Create Callback Page** (`frontend/src/pages/GoogleCallbackPage.tsx`)
   - Parse code and state from URL query params
   - Call API to exchange code for token
   - Handle success: save token, redirect to rankings
   - Handle errors: display message, link back to login
   - Handle account linking response (if implemented)

4. **Update AuthContext** (`frontend/src/context/AuthContext.tsx`)
   - Add `loginWithGoogle()` method
   - Redirect to Google authorization URL
   - Handle callback token save

5. **Update App Routing** (`frontend/src/App.tsx`)
   - Add route for `/auth/google/callback`

6. **Add MSW Handlers** (`frontend/src/__tests__/mocks/handlers.ts`)
   - Mock Google auth endpoints for testing

### Acceptance Criteria

- [ ] Clicking Google button redirects to Google
- [ ] Returning from Google exchanges code for JWT
- [ ] Token is saved and user is redirected to rankings
- [ ] Errors show clear messages with retry option
- [ ] Account linking flow works (if email exists)
- [ ] All API calls include trailing slashes

### Error Handling

| Error | User Message |
|-------|--------------|
| User cancelled | "Sign in was cancelled. Please try again." |
| Invalid state | "Authentication expired. Please try again." |
| Token exchange failed | "Authentication failed. Please try again." |
| Network error | "Connection error. Please check your network." |

---

## Task 5: Backend Tests

**Agent**: `qa-test-engineer`
**Priority**: P1 (High)
**Dependencies**: Task 2
**Estimated Effort**: Medium

### Description

Write comprehensive tests for the Google OAuth backend implementation.

### Deliverables

1. **Create Test File** (`tests/test_google_auth.py`)

   **Test Cases:**
   - `test_get_google_auth_url_returns_valid_url`
   - `test_callback_with_valid_code_creates_new_user`
   - `test_callback_with_valid_code_returns_jwt`
   - `test_callback_with_existing_google_id_finds_user`
   - `test_callback_with_existing_email_links_accounts`
   - `test_callback_with_invalid_state_returns_400`
   - `test_callback_with_expired_state_returns_400`
   - `test_callback_with_invalid_code_returns_400`
   - `test_callback_without_verified_email_returns_400`
   - `test_user_can_login_with_password_after_google_link`
   - `test_trailing_slashes_on_all_endpoints`

2. **Create Test Fixtures** (`tests/conftest.py` additions)
   - `mock_google_token_verification` fixture
   - `google_oauth_state` fixture
   - `google_user` fixture (user with google_id)

3. **Mock Google Token Validation**
   - Use pytest-mock to mock `google.oauth2.id_token.verify_oauth2_token`
   - Return controlled claims for testing

### Acceptance Criteria

- [ ] All test cases pass
- [ ] Edge cases (invalid state, expired state, unverified email) are covered
- [ ] Tests use async patterns matching existing tests
- [ ] No real Google API calls in tests
- [ ] Test coverage for happy path and error paths

### Test Patterns

Follow existing test patterns in `tests/test_auth.py`:
- Use `client` and `auth_headers` fixtures
- Assert status codes first, then response body
- Test 401/403/400 error scenarios
- Use trailing slashes on all URLs

---

## Task 6: Frontend Tests

**Agent**: `qa-test-engineer`
**Priority**: P1 (High)
**Dependencies**: Task 4, Task 5
**Estimated Effort**: Medium

### Description

Write tests for the Google OAuth frontend components and integration.

### Deliverables

1. **Component Tests** (`frontend/src/components/GoogleSignInButton.test.tsx`)
   - Test button renders with correct text
   - Test loading state shows spinner
   - Test click handler is called
   - Test disabled state

2. **Callback Page Tests** (`frontend/src/pages/GoogleCallbackPage.test.tsx`)
   - Test successful callback redirects to rankings
   - Test error displays message
   - Test loading state during token exchange
   - Test account linking flow

3. **Integration Tests**
   - Test full login flow with MSW mocks
   - Test error handling for various scenarios
   - Test auth state updates after Google login

4. **Update MSW Handlers** (`frontend/src/__tests__/mocks/handlers.ts`)
   - Add handlers for Google auth endpoints
   - Include success and error scenarios

### Acceptance Criteria

- [ ] GoogleSignInButton component has full test coverage
- [ ] GoogleCallbackPage has full test coverage
- [ ] MSW handlers mock all Google auth endpoints
- [ ] Tests pass in CI

---

## Task 7: Environment Configuration & Documentation

**Agent**: `devops-platform-engineer`
**Priority**: P2 (Medium)
**Dependencies**: Task 5, Task 6
**Estimated Effort**: Small

### Description

Update environment configuration and documentation for Google OAuth deployment.

### Deliverables

1. **Update docker-compose.yml**
   - Add Google OAuth environment variables
   - Reference `.env` file for secrets

2. **Update README.md**
   - Add section on Google OAuth setup
   - Document required environment variables
   - Link to Google Cloud Console setup instructions

3. **Create Setup Guide** (`.claude/plans/08-google-oauth/SETUP.md`)
   - Step-by-step Google Cloud Console setup
   - How to get client ID and secret
   - Configure redirect URIs for development and production

4. **Update Production Config** (if applicable)
   - Ensure production redirect URI is configured
   - Verify HTTPS requirement for production

### Acceptance Criteria

- [ ] Developers can set up Google OAuth from documentation
- [ ] docker-compose works with new environment variables
- [ ] Production deployment considerations are documented
- [ ] No secrets committed to repository

---

## Summary

| Task | Agent | Priority | Effort | Dependencies |
|------|-------|----------|--------|--------------|
| 1. Database & Config | backend-engineer | P0 | Small | None |
| 2. OAuth Endpoints | backend-engineer | P0 | Medium | Task 1 |
| 3. Google Button UI | frontend-react-engineer | P0 | Small | Task 2 |
| 4. OAuth Flow Integration | frontend-react-engineer | P0 | Medium | Task 3 |
| 5. Backend Tests | qa-test-engineer | P1 | Medium | Task 2 |
| 6. Frontend Tests | qa-test-engineer | P1 | Medium | Task 4, 5 |
| 7. Environment & Docs | devops-platform-engineer | P2 | Small | Task 5, 6 |

## Execution Notes

1. Execute tasks in order, waiting for completion before proceeding
2. Backend tasks (1-2) must complete before frontend tasks (3-4)
3. QA tasks (5-6) can begin once their dependencies complete
4. DevOps task (7) is lower priority and can be done last
5. All agents should follow patterns established in CLAUDE.md files
