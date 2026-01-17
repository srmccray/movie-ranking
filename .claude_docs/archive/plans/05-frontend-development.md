# Movie Ranking Frontend Development Plan

## Executive Summary

This plan outlines the coordinated development of a responsive, lightweight frontend for the existing Movie Ranking API. The backend is a complete FastAPI application with JWT authentication, movie management, and ranking functionality.

---

## Phase 0: Backend API Analysis (Complete)

### API Endpoints Summary

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | No | Health check |
| POST | `/api/v1/auth/register` | No | Create account, returns JWT |
| POST | `/api/v1/auth/login` | No | Login with OAuth2 form, returns JWT |
| POST | `/api/v1/movies/` | Yes | Add a movie (title, optional year) |
| POST | `/api/v1/rankings/` | Yes | Create/update ranking (1-5 scale) |
| GET | `/api/v1/rankings/` | Yes | List user's rankings (paginated) |

### Data Contracts

**Authentication:**
- Request: `{ email: string, password: string (min 8 chars) }`
- Login uses OAuth2 form: `username=email&password=...`
- Response: `{ access_token: string, token_type: "bearer" }`

**Movie:**
- Create: `{ title: string (1-500 chars), year?: number (1888-2031) }`
- Response: `{ id: UUID, title: string, year?: number, created_at: datetime }`

**Ranking:**
- Create: `{ movie_id: UUID, rating: number (1-5) }`
- Response: `{ id: UUID, movie_id: UUID, rating: number, created_at: datetime, updated_at: datetime }`
- List Response: `{ items: RankingWithMovie[], total: number, limit: number, offset: number }`

**RankingWithMovie:**
```typescript
{
  id: UUID,
  rating: number,
  created_at: datetime,
  updated_at: datetime,
  movie: { id: UUID, title: string, year?: number }
}
```

### CORS Configuration
- Backend allows `http://localhost:3000` (React dev server)
- All methods and headers allowed
- Credentials supported

---

## Phase 1: Product Definition

### Coordination with Product Manager Agent

**Objective:** Define user stories, acceptance criteria, and feature prioritization for the frontend.

**Key Inputs to Provide:**
1. Backend capabilities and constraints
2. MVP scope from existing documentation
3. Technical feasibility notes

**Expected Outputs:**
- User stories for frontend features
- Acceptance criteria for each story
- Priority ranking (P0/P1/P2)
- Core user flows

**Preliminary User Flows (for discussion):**
1. **Registration Flow:** Landing -> Register Form -> Success -> Dashboard
2. **Login Flow:** Landing -> Login Form -> Dashboard
3. **Add Movie Flow:** Dashboard -> Add Movie Modal/Form -> See in List
4. **Rank Movie Flow:** Movie Card -> Rating Selection -> Confirmation
5. **View Rankings Flow:** Dashboard -> Scrollable/Paginated List

---

## Phase 2: UX/UI Design

### Coordination with UX/UI Designer Agent

**Objective:** Create a clean, responsive design system and component specifications.

**Key Inputs to Provide:**
1. User stories from Phase 1
2. Data structures and API response shapes
3. Mobile-first requirement
4. Lightweight constraint (minimal animations/heavy graphics)

**Expected Outputs:**
- Design tokens (colors, typography, spacing)
- Component specifications with responsive breakpoints
- Page layouts (mobile and desktop)
- Interaction patterns
- Accessibility considerations

**Preliminary Component List:**
- Header/Navigation
- Auth Forms (Login/Register)
- Movie Card
- Rating Component (1-5 stars/numbers)
- Add Movie Form
- Rankings List (with pagination)
- Empty State
- Loading State
- Error State/Toast
- Modal (for add movie)

---

## Phase 3: Frontend Implementation

### Coordination with Frontend React Engineer Agent

**Objective:** Implement a lightweight React application matching the design system.

**Key Inputs to Provide:**
1. Design specifications from Phase 2
2. API contracts from Phase 0
3. Component hierarchy
4. State management requirements

**Expected Outputs:**
- React application structure
- Component implementations
- API integration layer
- Error handling
- Responsive CSS
- Basic test coverage

**Technical Recommendations:**
- **Framework:** React 18+ with Vite (lightweight, fast builds)
- **Styling:** CSS Modules or vanilla CSS (minimal bundle)
- **State:** React Context + useReducer (no Redux needed for MVP)
- **HTTP:** Fetch API (no axios dependency needed)
- **Routing:** React Router v6 (lightweight)
- **Types:** TypeScript for API contracts

**Project Structure:**
```
frontend/
├── src/
│   ├── api/              # API client and types
│   ├── components/       # Reusable UI components
│   ├── contexts/         # Auth context, etc.
│   ├── hooks/            # Custom hooks
│   ├── pages/            # Route components
│   ├── styles/           # Global styles, design tokens
│   ├── utils/            # Helpers
│   ├── App.tsx
│   └── main.tsx
├── index.html
├── vite.config.ts
├── tsconfig.json
└── package.json
```

---

## Phase 4: Backend Verification

### Coordination with Backend Engineer Agent

**Objective:** Verify API compatibility and address integration concerns.

**Key Items to Verify:**
1. CORS configuration is correct for production
2. Error response format consistency
3. Token expiration handling (24h tokens)
4. Pagination edge cases
5. Rate limiting considerations (documented as future)

**Potential Adjustments:**
- May need to add `/api/v1/auth/me` endpoint for token validation
- Verify token refresh strategy (currently none - 24h expiry)

---

## Phase 5: DevOps and Deployment

### Coordination with DevOps Platform Engineer Agent

**Objective:** Set up build configuration and deployment.

**Key Inputs to Provide:**
1. Frontend build output
2. Environment variable requirements
3. Static file serving needs

**Expected Outputs:**
- Vite build configuration
- Dockerfile for frontend (if containerized)
- Nginx configuration (for production serving)
- Environment variable handling
- CI/CD pipeline (optional for MVP)

**Deployment Options:**
1. **Simple:** Serve static build from backend (FastAPI static files)
2. **Separate:** Deploy frontend to CDN/static host (Vercel, Netlify)
3. **Containerized:** Add frontend container to docker-compose

---

## Coordination Sequence

```
Phase 1: Product Manager
    |
    v
Phase 2: UX/UI Designer
    |
    v
Phase 3: Frontend React Engineer
    |
    +-----> Phase 4: Backend Engineer (parallel verification)
    |
    v
Phase 5: DevOps Platform Engineer
```

**Rationale for Sequence:**
1. Product defines what we build (requirements)
2. Design defines how it looks (specifications)
3. Frontend implements (code)
4. Backend verifies compatibility (integration)
5. DevOps deploys (infrastructure)

---

## Success Criteria

1. **Functional:** All user stories implemented and working
2. **Responsive:** Works on mobile (320px) to desktop (1920px)
3. **Lightweight:** Initial bundle < 100KB gzipped
4. **Accessible:** Basic WCAG 2.1 AA compliance
5. **Integrated:** Seamlessly works with existing backend
6. **Documented:** Setup and deployment instructions

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| API contract mismatch | Low | High | Verify contracts before implementation |
| CORS issues in production | Medium | Medium | Test early, configure properly |
| Token expiration UX | Medium | Medium | Graceful logout, clear error messages |
| Bundle size creep | Medium | Low | Minimal dependencies, monitor size |
| Mobile responsiveness issues | Low | Medium | Mobile-first development |

---

## Next Steps

1. **Start Phase 1:** Coordinate with Product Manager to finalize user stories
2. **Confirm scope:** Ensure MVP boundaries are clear
3. **Proceed sequentially** through each phase, validating outputs before moving on

---

## Appendix: TypeScript API Types

```typescript
// types/api.ts

// Auth
interface UserCreate {
  email: string;
  password: string;
}

interface Token {
  access_token: string;
  token_type: "bearer";
}

// Movie
interface MovieCreate {
  title: string;
  year?: number;
}

interface Movie {
  id: string;
  title: string;
  year: number | null;
  created_at: string;
}

interface MovieBrief {
  id: string;
  title: string;
  year: number | null;
}

// Ranking
interface RankingCreate {
  movie_id: string;
  rating: number; // 1-5
}

interface Ranking {
  id: string;
  movie_id: string;
  rating: number;
  created_at: string;
  updated_at: string;
}

interface RankingWithMovie {
  id: string;
  rating: number;
  created_at: string;
  updated_at: string;
  movie: MovieBrief;
}

interface RankingListResponse {
  items: RankingWithMovie[];
  total: number;
  limit: number;
  offset: number;
}

// Error
interface APIError {
  detail: string | ValidationError[];
}

interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}
```
