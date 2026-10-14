# Google Account Linking - Task Tracking

## Status: Completed

## Phase 1: Backend Implementation

### Task 1.1: Database Migration
- **Status**: Pending
- **Assignee**: backend-engineer
- **Description**: Add `user_id` and `flow_type` columns to `oauth_states` table
- **Files**:
  - `alembic/versions/00X_add_oauth_state_linking_fields.py`
  - `app/models/oauth_state.py`

### Task 1.2: Schema Updates
- **Status**: Pending
- **Assignee**: backend-engineer
- **Description**: Update OAuth and User schemas
- **Files**:
  - `app/schemas/oauth.py` - Add `GoogleLinkStatusResponse`
  - `app/schemas/user.py` - Add `UserProfileResponse` with auth_provider

### Task 1.3: User Profile Endpoint
- **Status**: Pending
- **Assignee**: backend-engineer
- **Description**: Add `GET /api/v1/auth/me/` endpoint
- **Files**:
  - `app/routers/auth.py`

### Task 1.4: Link Initiation Endpoint
- **Status**: Pending
- **Assignee**: backend-engineer
- **Description**: Add `GET /api/v1/auth/google/link/` endpoint
- **Files**:
  - `app/routers/google_auth.py`

### Task 1.5: Link Callback Endpoint
- **Status**: Pending
- **Assignee**: backend-engineer
- **Description**: Add `GET /api/v1/auth/google/link/callback/` endpoint
- **Files**:
  - `app/routers/google_auth.py`

### Task 1.6: Backend Tests
- **Status**: Pending
- **Assignee**: backend-engineer
- **Description**: Tests for linking flow
- **Files**:
  - `tests/test_google_auth_linking.py`

---

## Phase 2: Frontend Implementation

### Task 2.1: Type Definitions
- **Status**: Pending
- **Assignee**: frontend-react-engineer
- **Description**: Add/update types for user profile and linking
- **Files**:
  - `frontend/src/types/index.ts`

### Task 2.2: API Client Updates
- **Status**: Pending
- **Assignee**: frontend-react-engineer
- **Description**: Add API methods for linking and user profile
- **Files**:
  - `frontend/src/api/client.ts`

### Task 2.3: Settings Page
- **Status**: Pending
- **Assignee**: frontend-react-engineer
- **Description**: Create Settings page with Google link functionality
- **Files**:
  - `frontend/src/pages/SettingsPage.tsx`
  - `frontend/src/index.css` (styles)

### Task 2.4: Link Callback Page
- **Status**: Pending
- **Assignee**: frontend-react-engineer
- **Description**: Handle linking callback route
- **Files**:
  - `frontend/src/pages/GoogleLinkCallbackPage.tsx`

### Task 2.5: Navigation Update
- **Status**: Pending
- **Assignee**: frontend-react-engineer
- **Description**: Add Settings link to Header
- **Files**:
  - `frontend/src/components/Header.tsx`

### Task 2.6: App Router Update
- **Status**: Pending
- **Assignee**: frontend-react-engineer
- **Description**: Add routes for settings and link callback
- **Files**:
  - `frontend/src/App.tsx`

### Task 2.7: Frontend Tests
- **Status**: Pending
- **Assignee**: frontend-react-engineer
- **Description**: Component tests and MSW handlers
- **Files**:
  - `frontend/src/pages/SettingsPage.test.tsx`
  - `frontend/src/__tests__/mocks/handlers.ts`

---

## Phase 3: QA

### Task 3.1: Integration Testing
- **Status**: Pending
- **Assignee**: qa-test-engineer
- **Description**: End-to-end testing of linking flow

---

## Completion Checklist

- [x] All backend endpoints implemented and tested
- [x] All frontend components implemented and tested
- [x] Settings page accessible from navigation
- [x] Linking flow works end-to-end
- [x] Error handling covers all edge cases
- [x] Code follows project conventions (trailing slashes, naive UTC, etc.)
