# Movie Ranking API - Product Features (MVP)

## Overview

The Movie Ranking API enables users to create personal movie rankings on a 1-5 scale. This MVP focuses on core functionality: user authentication, manual movie entry, and personal ranking management.

**Target Users:** Movie enthusiasts who want to track and rank films they've watched.

**Value Proposition:** Simple, personal movie ranking without the complexity of social features or external integrations.

---

## User Stories

### Epic 1: User Authentication

#### US-1.1: User Registration
**As a** new user
**I want to** create an account with email and password
**So that** I can securely store my movie rankings

**Acceptance Criteria:**
- User provides email and password to register
- Email must be unique and valid format
- Password must be at least 8 characters
- System returns JWT access token upon successful registration
- System returns 400 error for invalid email format
- System returns 409 error if email already exists
- System returns 422 error if password is too short

**Technical Notes:**
- Password stored using bcrypt hashing
- JWT token includes user_id claim
- Token expiration: 24 hours

---

#### US-1.2: User Login
**As a** registered user
**I want to** log in with my email and password
**So that** I can access my movie rankings

**Acceptance Criteria:**
- User provides email and password to authenticate
- System returns JWT access token upon successful login
- System returns 401 error for invalid credentials
- Token can be used in Authorization header for protected endpoints

**Technical Notes:**
- Use OAuth2 password flow for compatibility
- Return token_type: "bearer"

---

### Epic 2: Movie Management

#### US-2.1: Add a Movie
**As an** authenticated user
**I want to** add a movie to the system
**So that** I can rank it later

**Acceptance Criteria:**
- User provides movie title (required) and year (optional)
- System creates the movie record
- System returns the created movie with its ID
- Movie title must be non-empty string
- Year must be a valid 4-digit year (1888-current year + 5)
- System returns 401 error if user is not authenticated
- System returns 422 error for invalid input

**Technical Notes:**
- Movies are global (shared across users)
- Duplicate title+year combinations are allowed (different editions/versions)

---

### Epic 3: Movie Rankings

#### US-3.1: Rank a Movie
**As an** authenticated user
**I want to** assign a ranking (1-5) to a movie
**So that** I can record my opinion of it

**Acceptance Criteria:**
- User provides movie_id and ranking (1-5 integer)
- System creates or updates the user's ranking for that movie
- Ranking must be an integer between 1 and 5 inclusive
- System returns 401 error if user is not authenticated
- System returns 404 error if movie does not exist
- System returns 422 error if ranking is not 1-5 integer
- If user has already ranked this movie, the ranking is updated

**Rating Scale:**
| Rating | Meaning |
|--------|---------|
| 1 | Poor |
| 2 | Below Average |
| 3 | Average |
| 4 | Good |
| 5 | Excellent |

**Technical Notes:**
- One ranking per user per movie (upsert behavior)
- Rankings are private to each user

---

#### US-3.2: List My Rankings
**As an** authenticated user
**I want to** see all movies I have ranked
**So that** I can review my rankings

**Acceptance Criteria:**
- System returns list of all movies the user has ranked
- Each item includes: movie title, movie year, user's ranking, ranked_at timestamp
- List is ordered by most recently ranked first
- Returns empty list if user has no rankings
- System returns 401 error if user is not authenticated

**Technical Notes:**
- Include pagination for future scalability (limit/offset)
- Default limit: 20, max limit: 100

---

## Feature Specifications

### Authentication System

| Feature | Specification |
|---------|---------------|
| Auth Method | JWT Bearer Token |
| Token Lifetime | 24 hours |
| Password Hashing | bcrypt |
| Min Password Length | 8 characters |
| Email Validation | RFC 5322 format |

### Rating System

| Feature | Specification |
|---------|---------------|
| Scale | 1-5 integers only |
| Behavior | One rating per user per movie |
| Update Policy | Re-rating overwrites previous |
| Visibility | Private (user sees only own ratings) |

### Data Constraints

| Entity | Field | Constraint |
|--------|-------|------------|
| User | email | Unique, valid email format |
| User | password | Min 8 characters |
| Movie | title | Required, non-empty string |
| Movie | year | Optional, 1888 to current+5 |
| Ranking | value | Integer 1-5 |

---

## Out of Scope (MVP)

The following features are explicitly excluded from MVP:

- **Search/Browse Movies:** No search or filtering functionality
- **Update/Delete Rankings:** Users cannot modify or remove rankings
- **Average Ratings:** No aggregated ratings across users
- **Social Features:** No following, sharing, or public profiles
- **External API Integration:** No TMDB, IMDB, or other movie databases
- **Movie Details:** No poster images, descriptions, or cast information
- **User Profile Management:** No profile editing or password reset

---

## Success Metrics (Post-Launch)

- Users can complete registration in under 30 seconds
- API response times under 200ms (p95)
- Zero security vulnerabilities in authentication flow
- 99.9% uptime

---

## Future Considerations (v2+)

1. Search and filter movies
2. Update/delete rankings
3. Average ratings display
4. Movie details from external API
5. Public/private profile options
6. Social features (follow, share lists)
