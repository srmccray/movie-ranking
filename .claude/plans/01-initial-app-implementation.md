# Movie Ranking App - Implementation Plan

## Overview
A full-featured movie ranking app with React frontend, FastAPI backend, and PostgreSQL database.

## Data Model
| Field | Type | Constraints |
|-------|------|-------------|
| id | Integer | Primary key, auto-increment |
| title | String(255) | Required |
| watched_date | Date | Required |
| ranking | Integer | 1-5 range |
| created_at | Timestamp | Auto-generated |
| updated_at | Timestamp | Auto-updated |

## Project Structure
```
movie-ranking/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app entry point
│   │   ├── config.py         # Environment settings
│   │   ├── database.py       # DB connection
│   │   ├── models/movie.py   # SQLAlchemy model
│   │   ├── schemas/movie.py  # Pydantic schemas
│   │   ├── routers/movies.py # API endpoints
│   │   └── services/movie_service.py
│   ├── alembic/              # DB migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── movies/       # MovieCard, MovieList, MovieForm, MovieFilters
│   │   │   └── common/       # Button, Input, RatingStars
│   │   ├── hooks/use-movies.ts
│   │   ├── services/movie-service.ts
│   │   ├── types/movie.ts
│   │   └── App.tsx
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/movies` | List movies (supports `search`, `rating`, `sort_by`, `sort_order`, `skip`, `limit`) |
| GET | `/api/v1/movies/{id}` | Get single movie |
| POST | `/api/v1/movies` | Create movie |
| PUT | `/api/v1/movies/{id}` | Update movie |
| DELETE | `/api/v1/movies/{id}` | Delete movie |

## Implementation Order (with Agent Assignments)

### Phase 1: Infrastructure Setup → `devops-platform-engineer`
1. Create project directory structure
2. Create docker-compose.yml with PostgreSQL service
3. Create backend Dockerfile
4. Create frontend Dockerfile
5. Set up .gitignore and environment file templates

### Phase 2: Backend Development → `backend-engineer`
1. Initialize FastAPI project with dependencies (requirements.txt)
2. Create app configuration and database connection
3. Create SQLAlchemy Movie model
4. Set up Alembic and create initial migration
5. Create Pydantic schemas for request/response validation
6. Implement movie service layer (CRUD operations)
7. Create router with all endpoints (list, get, create, update, delete)
8. Add filtering, sorting, and search logic

### Phase 3: Frontend Development → `frontend-react-engineer`
1. Initialize Vite + React + TypeScript project
2. Set up API service with Axios
3. Create TypeScript interfaces for Movie types
4. Implement `useMovies` custom hook with React Query
5. Build UI components: MovieCard, MovieList, MovieForm, MovieFilters, RatingStars
6. Assemble main page with all features
7. Add styling and responsive design

### Phase 4: Testing → `qa-test-engineer`
1. Write pytest tests for backend API endpoints
2. Write React Testing Library tests for frontend components
3. Verify end-to-end functionality

## Key Dependencies

**Backend:**
- fastapi, uvicorn, sqlalchemy, psycopg2-binary, alembic, pydantic, pydantic-settings

**Frontend:**
- react, react-dom, @tanstack/react-query, axios, typescript, vite

## How to Run

```bash
# Start all services with Docker
docker-compose up -d

# Run database migrations
docker-compose exec backend alembic upgrade head

# Access:
# - Frontend: http://localhost:5173
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

## Verification
1. Start services with `docker-compose up`
2. Open http://localhost:8000/docs to verify API is running
3. Open http://localhost:5173 to verify frontend loads
4. Test full flow: Add a movie, verify it appears, edit it, filter/sort, delete it
