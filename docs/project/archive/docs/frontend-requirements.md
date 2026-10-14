# Movie Ranking Frontend - Product Requirements

## Overview

A lightweight, responsive React frontend for the Movie Ranking API that enables users to register, login, add movies, create rankings, and view their ranked movies.

**Target Bundle Size:** < 100KB gzipped
**Primary Stack:** Vite + React + TypeScript

---

## User Stories

### Epic 1: Authentication

#### US-F1.1: User Registration
**As a** new user
**I want to** create an account with my email and password
**So that** I can start ranking movies

**Acceptance Criteria:**
- Given I am on the registration page, I see email and password input fields
- Given I enter a valid email and password (8+ chars), when I submit, then I am logged in and redirected to the rankings page
- Given I enter an invalid email format, when I submit, then I see an inline error "Please enter a valid email"
- Given I enter a password less than 8 characters, when I submit, then I see an inline error "Password must be at least 8 characters"
- Given the email is already registered, when I submit, then I see an error "This email is already registered"
- Given the form is submitting, then I see a loading indicator and the submit button is disabled

**Definition of Done:**
- [ ] Registration form with email/password fields
- [ ] Client-side validation before API call
- [ ] API error handling with user-friendly messages
- [ ] Loading state during submission
- [ ] JWT token stored securely (memory/httpOnly consideration)
- [ ] Automatic redirect to rankings after success

---

#### US-F1.2: User Login
**As a** returning user
**I want to** log in with my credentials
**So that** I can access my movie rankings

**Acceptance Criteria:**
- Given I am on the login page, I see email and password input fields
- Given I enter valid credentials, when I submit, then I am logged in and redirected to the rankings page
- Given I enter invalid credentials, when I submit, then I see an error "Invalid email or password"
- Given the form is submitting, then I see a loading indicator
- Given I am logged in, I should see a way to log out

**Definition of Done:**
- [ ] Login form with email/password fields
- [ ] API integration with OAuth2 form format
- [ ] Error handling for 401 responses
- [ ] Loading state during submission
- [ ] Redirect to rankings after success
- [ ] Link to registration page

---

#### US-F1.3: Session Management
**As a** logged-in user
**I want** my session to persist until I log out
**So that** I don't have to log in repeatedly

**Acceptance Criteria:**
- Given I am logged in, when I refresh the page, then I remain logged in
- Given I click logout, then I am logged out and redirected to login
- Given my token expires, when I make an API call, then I am redirected to login

**Definition of Done:**
- [ ] Token persistence (localStorage or sessionStorage)
- [ ] Logout functionality
- [ ] Auth state checked on app load
- [ ] Automatic redirect on 401 responses

---

### Epic 2: Movie Management

#### US-F2.1: Add a Movie
**As an** authenticated user
**I want to** add a new movie
**So that** I can rank it

**Acceptance Criteria:**
- Given I am on the add movie page/modal, I see title (required) and year (optional) fields
- Given I enter a valid title, when I submit, then the movie is created
- Given I leave the title empty, when I try to submit, then I see an error "Title is required"
- Given I enter an invalid year (before 1888 or after 2031), when I submit, then I see an error
- Given the movie is created successfully, then I can immediately rank it

**Definition of Done:**
- [ ] Add movie form/modal with title and year fields
- [ ] Client-side validation
- [ ] API integration
- [ ] Success feedback to user
- [ ] Option to immediately rank the newly added movie

---

### Epic 3: Rankings

#### US-F3.1: Rate a Movie
**As an** authenticated user
**I want to** assign a 1-5 star rating to a movie
**So that** I can record my opinion

**Acceptance Criteria:**
- Given I have added a movie, I can select a rating from 1-5
- Given I select a rating, when I submit, then the rating is saved
- Given I have already rated a movie, when I rate it again, then the rating is updated
- Given the API returns an error, then I see an appropriate error message

**Definition of Done:**
- [ ] Star rating component (1-5 stars)
- [ ] Visual feedback on rating selection
- [ ] API integration for creating/updating rankings
- [ ] Loading state during submission
- [ ] Success feedback

---

#### US-F3.2: View My Rankings
**As an** authenticated user
**I want to** see all the movies I have ranked
**So that** I can review my rankings

**Acceptance Criteria:**
- Given I am on the rankings page, I see a list of movies I have ranked
- Given the list includes movie title, year, and my rating (as stars)
- Given I have no rankings, I see an empty state message
- Given there are many rankings, the list is paginated or scrollable
- Given the list is loading, I see a loading indicator

**Definition of Done:**
- [ ] Rankings list component
- [ ] Display movie title, year, and rating
- [ ] Empty state for no rankings
- [ ] Loading state
- [ ] Pagination support (load more or infinite scroll)

---

## Page Structure

### Pages Required

1. **Login Page** (`/login`)
   - Login form
   - Link to register

2. **Register Page** (`/register`)
   - Registration form
   - Link to login

3. **Rankings Page** (`/` or `/rankings`) - Protected
   - List of user's ranked movies
   - Button to add a new movie
   - Each ranking shows movie info and rating

4. **Add Movie Page/Modal** - Protected
   - Form to add movie title and year
   - After adding, option to rate immediately

---

## Technical Requirements

### Bundle Size Optimization
- Target: < 100KB gzipped total
- Use Vite for fast builds and tree shaking
- Minimal dependencies:
  - React 18 (core)
  - React Router (routing)
  - Minimal or no UI library (custom CSS)
- No heavy state management libraries

### Responsive Design
- Mobile-first approach
- Breakpoints: 320px (mobile), 768px (tablet), 1024px+ (desktop)
- Touch-friendly tap targets (44px minimum)

### API Integration
- Base URL configurable via environment variable
- JWT token included in Authorization header
- Proper error handling for all API responses
- Loading states for all async operations

### Accessibility
- Semantic HTML
- ARIA labels where needed
- Keyboard navigation support
- Focus management on route changes
- Color contrast compliance

---

## Success Metrics

- First Contentful Paint < 1.5s
- Time to Interactive < 3s
- Bundle size < 100KB gzipped
- Lighthouse score > 90 for Performance, Accessibility
- All user flows completable on mobile devices

---

## Out of Scope (MVP)

- Search/filter movies
- Edit/delete rankings
- Password reset
- Social features
- Offline support
- Dark mode (could add if time permits)
