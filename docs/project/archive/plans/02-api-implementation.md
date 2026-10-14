# Movie Ranking API - Implementation Plan

## Summary
Build a FastAPI backend for a movie ranking website with PostgreSQL database and JWT authentication, designed for future React frontend integration.

## Confirmed Requirements
- **Auth:** User registration + login with JWT tokens
- **Movies:** Users add movies manually (title + optional year)
- **Rankings:** Integer scale 1-5, one rating per user per movie (upsert behavior)
- **MVP Scope:** Basic only - no search, no average ratings, no delete functionality

## Documentation Created
The following specs have been created and should guide implementation:
- `/docs/features.md` - User stories and acceptance criteria
- `/docs/architecture.md` - Database schema, project structure, ADRs
- `/docs/api-spec.md` - Endpoint specifications with examples

---

## Implementation Steps

### Phase 1: Project Setup
1. Initialize Python project with `pyproject.toml`
2. Install dependencies: FastAPI, SQLAlchemy 2.0 (async), Alembic, python-jose, passlib, uvicorn, asyncpg
3. Create project structure:
   ```
   app/
   ├── main.py
   ├── config.py
   ├── database.py
   ├── dependencies.py
   ├── models/
   ├── schemas/
   ├── routers/
   ├── services/
   └── utils/
   ```
4. Create `.env.example` with required environment variables

### Phase 2: Database
1. Configure async SQLAlchemy with PostgreSQL
2. Create SQLAlchemy models: `User`, `Movie`, `Ranking`
3. Set up Alembic for migrations
4. Create initial migration with all three tables

### Phase 3: Authentication
1. Implement password hashing utilities (bcrypt)
2. Implement JWT token creation/verification
3. Create `get_current_user` dependency
4. Build auth router with:
   - `POST /api/v1/auth/register`
   - `POST /api/v1/auth/login` (OAuth2 password flow)

### Phase 4: Core API
1. Create Pydantic schemas for all endpoints
2. Build movies router: `POST /api/v1/movies`
3. Build rankings router:
   - `POST /api/v1/rankings` (with upsert logic)
   - `GET /api/v1/rankings` (with pagination)

### Phase 5: Configuration & Polish
1. Add CORS middleware for React frontend
2. Configure error handling
3. Create requirements.txt

---

## Critical Files to Create

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app entry point, middleware, router includes |
| `app/config.py` | Settings from environment variables |
| `app/database.py` | Async SQLAlchemy engine and session |
| `app/models/user.py` | User SQLAlchemy model |
| `app/models/movie.py` | Movie SQLAlchemy model |
| `app/models/ranking.py` | Ranking SQLAlchemy model |
| `app/routers/auth.py` | Registration and login endpoints |
| `app/routers/movies.py` | Movie creation endpoint |
| `app/routers/rankings.py` | Ranking CRUD endpoints |
| `app/utils/security.py` | Password hashing, JWT utilities |

---

## Database Schema

```sql
-- users: id (UUID), email, hashed_password, timestamps
-- movies: id (UUID), title, year, timestamps
-- rankings: id (UUID), user_id (FK), movie_id (FK), rating (1-5), timestamps
--           UNIQUE(user_id, movie_id)
```

---

## API Endpoints (5 total)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | /api/v1/auth/register | No | Create account, return JWT |
| POST | /api/v1/auth/login | No | Login, return JWT |
| POST | /api/v1/movies | Yes | Add movie |
| POST | /api/v1/rankings | Yes | Create/update ranking |
| GET | /api/v1/rankings | Yes | List user's rankings (paginated) |

---

## Verification Plan

1. **Start PostgreSQL** (Docker or local)
2. **Run migrations:** `alembic upgrade head`
3. **Start server:** `uvicorn app.main:app --reload`
4. **Test endpoints manually:**
   ```bash
   # Register
   curl -X POST http://localhost:8000/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email": "test@example.com", "password": "testpassword123"}'

   # Login
   curl -X POST http://localhost:8000/api/v1/auth/login \
     -d "username=test@example.com&password=testpassword123"

   # Add movie (use token from login)
   curl -X POST http://localhost:8000/api/v1/movies \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"title": "Inception", "year": 2010}'

   # Rank movie
   curl -X POST http://localhost:8000/api/v1/rankings \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"movie_id": "<movie-id>", "rating": 5}'

   # List rankings
   curl http://localhost:8000/api/v1/rankings \
     -H "Authorization: Bearer <token>"
   ```
5. **Check OpenAPI docs:** http://localhost:8000/docs

---

## Key Design Decisions

1. **UUID primary keys** - No enumeration attacks, distributed-ready
2. **Async SQLAlchemy** - Better performance with FastAPI
3. **Upsert for rankings** - Simpler UX, re-rating updates existing
4. **Global movie pool** - Movies shared across users (enables future average ratings)
5. **OAuth2 password flow** - Compatible with React auth libraries
