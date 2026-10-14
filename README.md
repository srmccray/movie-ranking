# Movie Ranking

A full-stack movie ranking application. Users can register, log in, search for movies, and rank them on a 1-5 scale.

## Current State

Full stack with a React frontend, a FastAPI backend, and AWS CDK infrastructure:

- User registration and login (JWT authentication), plus Google Sign-In and linking a Google account
- Movie search backed by TMDB (requires a TMDB API key) and adding movies to your library
- Rank movies 1-5 (upsert behavior - re-ranking updates existing)
- List your rankings with pagination; delete one ranking or all rankings
- Analytics: activity, genre breakdown, stats, and rating distribution
- Amazon Prime Video watch-history import (CSV upload, review/match each movie, add or skip)
- Settings, analytics, and auth pages in the React frontend
- AWS deployment (CloudFront, Lambda via Mangum) through GitHub Actions

## Tech Stack

### Backend
- **Framework:** FastAPI
- **Database:** PostgreSQL with async SQLAlchemy 2.0
- **Authentication:** JWT (python-jose) + bcrypt password hashing; Google OAuth (google-auth)
- **Validation:** Pydantic v2
- **External data:** TMDB API (via httpx)
- **Migrations:** Alembic
- **Lambda adapter:** Mangum
- **Runtime:** Python 3.12 (Docker image and deploy workflow; `pyproject.toml` requires >=3.11)

### Frontend
- **Framework:** React 18 with TypeScript 5.6
- **Build Tool:** Vite 6
- **Routing:** React Router 6
- **Styling:** CSS with custom properties (design tokens)
- **Testing:** Vitest, Testing Library, MSW

### Infrastructure
- **IaC:** AWS CDK v2 (TypeScript), see `infra/`

## Quick Start (Full Stack)

### Prerequisites
- Docker and Docker Compose
- Node.js 20+ (for frontend development; CI uses Node 20)

### Start Everything

```bash
# 1. Copy environment template (set SECRET_KEY and TMDB_API_KEY)
cp .env.example .env

# 2. Start the backend (database + API)
docker compose up -d

# 3. Run database migrations
docker compose exec api alembic upgrade head

# 4. Start the frontend (in a separate terminal)
cd frontend
npm install
npm run dev
```

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

## Project Structure

```
movie-ranking/
├── frontend/                 # React frontend application
│   ├── src/
│   │   ├── api/             # API client
│   │   ├── components/      # Reusable UI components
│   │   ├── context/         # React context (auth)
│   │   ├── hooks/           # Custom hooks
│   │   ├── pages/           # Page components
│   │   ├── styles/          # Design tokens and shared styles
│   │   ├── types/           # TypeScript types
│   │   └── __tests__/       # Test setup and shared tests
│   ├── package.json
│   └── vite.config.ts
├── app/                      # FastAPI backend
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings from environment
│   ├── database.py          # Async SQLAlchemy setup
│   ├── dependencies.py      # Auth dependencies
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── routers/             # API route handlers (auth, google_auth, movies,
│   │                        #   rankings, analytics, import_amazon)
│   ├── services/            # TMDB client, CSV parser, import sessions
│   └── utils/               # Utilities (security)
├── alembic/                  # Database migrations
├── tests/                    # Backend pytest suite
├── infra/                    # AWS CDK infrastructure (TypeScript)
├── lambda_handler.py         # Lambda entry point (Mangum)
├── .github/workflows/        # ci.yml, deploy.yml, deploy-pages.yml
├── docs/                     # SpecOps docs site sources
│   └── project/              # PRDs, backlog, user stories, ADRs, archive
├── specops.toml              # SpecOps configuration
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── requirements-test.txt
```

## Backend Development

### Docker Setup (Recommended)

The fastest way to get the backend running.

```bash
# Copy environment template
cp .env.example .env
# Edit .env to set SECRET_KEY and TMDB_API_KEY (both required by app/config.py)

# Start everything (database + API)
docker compose up
```

That's it. The API will be available at `http://localhost:8000`.

### Common Commands

```bash
# Start in background (detached mode)
docker compose up -d

# Stop all services
docker compose down

# Stop and remove volumes (resets database)
docker compose down -v

# Rebuild after code changes
docker compose up --build

# View logs
docker compose logs -f        # All services
docker compose logs -f api    # API only
docker compose logs -f db     # Database only

# Restart a specific service
docker compose restart api
```

### Run Migrations

Migrations are not run automatically on startup. Run them manually:

```bash
# Run pending migrations
docker compose exec api alembic upgrade head

# Create a new migration
docker compose exec api alembic revision --autogenerate -m "description"

# Rollback last migration
docker compose exec api alembic downgrade -1

# View migration history
docker compose exec api alembic history
```

### Access the Database

```bash
# Connect to PostgreSQL
docker compose exec db psql -U postgres -d movie_ranking

# Or use any PostgreSQL client with:
# Host: localhost, Port: 5432, User: postgres, Password: postgres, Database: movie_ranking
```

## Environment Variables

Configure via `.env` file or environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| SECRET_KEY | Yes | - | JWT signing key (use a secure random string) |
| DATABASE_URL | Yes | - | Async SQLAlchemy URL, e.g. `postgresql+asyncpg://user:password@localhost:5432/movie_ranking` (set by docker-compose for the `api` service) |
| TMDB_API_KEY | Yes | - | TMDB API key for movie search ([get one](https://www.themoviedb.org/settings/api)) |
| TMDB_BASE_URL | No | https://api.themoviedb.org/3 | TMDB API base URL |
| TMDB_IMAGE_BASE_URL | No | https://image.tmdb.org/t/p/w185 | TMDB poster base URL |
| POSTGRES_USER | No | postgres | Database user |
| POSTGRES_PASSWORD | No | postgres | Database password |
| POSTGRES_DB | No | movie_ranking | Database name |
| POSTGRES_PORT | No | 5432 | Host port for database |
| API_PORT | No | 8000 | Host port for API |
| ALGORITHM | No | HS256 | JWT algorithm |
| ACCESS_TOKEN_EXPIRE_MINUTES | No | 1440 | Token lifetime (24 hours) |
| DEBUG | No | false | Debug mode |
| GOOGLE_CLIENT_ID | No | - | Google OAuth client ID (for "Sign in with Google") |
| GOOGLE_CLIENT_SECRET | No | - | Google OAuth client secret |
| GOOGLE_REDIRECT_URI | No | http://localhost:8000/api/v1/auth/google/callback/ | OAuth callback URL |

Example `.env`:
```
SECRET_KEY=your-256-bit-secret-key-here
POSTGRES_PASSWORD=mysecurepassword
```

### Google OAuth Setup (Optional)

To enable "Sign in with Google", you need to create OAuth credentials in the Google Cloud Console:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Navigate to **APIs & Services > Credentials**
4. Click **Create Credentials > OAuth client ID**
5. Select **Web application** as the application type
6. Add authorized redirect URIs:
   - Development: `http://localhost:8000/api/v1/auth/google/callback/`
   - Production: `https://yourdomain.com/api/v1/auth/google/callback/`
7. Copy the Client ID and Client Secret to your `.env` file

```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

For detailed setup instructions, see [Google OAuth Setup Guide](docs/project/archive/plans/08-google-oauth/SETUP.md).

## Local Development (without Docker)

If you prefer running without Docker:

### Prerequisites

- Python 3.11+ (3.12 matches Docker and deploy)
- PostgreSQL 16+

### Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Set DATABASE_URL (postgresql+asyncpg://...), SECRET_KEY, and TMDB_API_KEY
```

### Run Locally

```bash
# Start PostgreSQL (example using Docker for just the database)
docker run -d --name movie-ranking-db \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=movie_ranking \
  -p 5432:5432 \
  postgres:16

# Run migrations
alembic upgrade head

# Start the server with hot reload
uvicorn app.main:app --reload
```

## API Documentation

Once running, interactive docs are available at:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Endpoints

All API routes except `/health`, `/api/v1/auth/register`, and `/api/v1/auth/login` use trailing slashes.

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | No | Health check |
| POST | `/api/v1/auth/register` | No | Create account (returns JWT) |
| POST | `/api/v1/auth/login` | No | Login, form-encoded (returns JWT) |
| GET | `/api/v1/auth/me/` | Yes | Current user |
| GET | `/api/v1/auth/google/login/` | No | Get Google OAuth URL |
| GET | `/api/v1/auth/google/callback/` | No | Handle Google OAuth callback |
| GET | `/api/v1/auth/google/link/` | Yes | Start linking a Google account |
| GET | `/api/v1/auth/google/link/callback/` | OAuth state | Finish linking a Google account |
| GET | `/api/v1/movies/search/` | Yes | Search TMDB for movies |
| POST | `/api/v1/movies/` | Yes | Add a movie |
| POST | `/api/v1/rankings/` | Yes | Create/update ranking |
| GET | `/api/v1/rankings/` | Yes | List your rankings |
| DELETE | `/api/v1/rankings/{ranking_id}/` | Yes | Delete one ranking |
| DELETE | `/api/v1/rankings/all/` | Yes | Delete all your rankings |
| GET | `/api/v1/analytics/activity/` | Yes | Ranking activity over time |
| GET | `/api/v1/analytics/genres/` | Yes | Genre breakdown |
| GET | `/api/v1/analytics/stats/` | Yes | Summary stats |
| GET | `/api/v1/analytics/rating-distribution/` | Yes | Rating distribution |
| POST | `/api/v1/import/amazon-prime/upload/` | Yes | Upload Prime Video CSV, start import session |
| GET | `/api/v1/import/amazon-prime/session/{session_id}/` | Yes | Get import session |
| POST | `/api/v1/import/amazon-prime/session/{session_id}/movie/{index}/add/` | Yes | Add matched movie |
| POST | `/api/v1/import/amazon-prime/session/{session_id}/movie/{index}/skip/` | Yes | Skip movie |
| PATCH | `/api/v1/import/amazon-prime/session/{session_id}/movie/{index}/match/` | Yes | Change the TMDB match |
| DELETE | `/api/v1/import/amazon-prime/session/{session_id}/` | Yes | Cancel import session |

## Testing

### Manual Testing with curl

```bash
# Register a user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpassword123"}'

# Login (save the access_token)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=test@example.com&password=testpassword123"

# Add a movie (replace TOKEN with your access_token)
curl -X POST http://localhost:8000/api/v1/movies/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Inception", "year": 2010}'

# Or search TMDB first
curl "http://localhost:8000/api/v1/movies/search/?q=inception" \
  -H "Authorization: Bearer TOKEN"

# Rank a movie (replace MOVIE_ID with the movie's id)
curl -X POST http://localhost:8000/api/v1/rankings/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"movie_id": "MOVIE_ID", "rating": 5}'

# List your rankings
curl http://localhost:8000/api/v1/rankings/ \
  -H "Authorization: Bearer TOKEN"
```

### Run Automated Tests

```bash
# Backend (from the repo root, using the local venv; tests use SQLite via aiosqlite)
venv/bin/pip install -r requirements-test.txt
venv/bin/pytest

# Frontend
cd frontend
npm run test:run     # single run (CI); `npm test` starts watch mode
npm run lint
npm run build        # tsc -b && vite build

# End-to-end (Playwright, Chromium; starts its own backend on throwaway SQLite + Vite)
npx playwright install chromium   # once
npm run test:e2e
```

## Troubleshooting

### API won't start

Check if the database is healthy:
```bash
docker compose ps
docker compose logs db
```

### Database connection errors

Ensure the database is running and healthy before the API starts:
```bash
docker compose down
docker compose up -d db
docker compose logs -f db  # Wait for "database system is ready to accept connections"
docker compose up api
```

### Reset everything

```bash
docker compose down -v
docker compose up --build
docker compose exec api alembic upgrade head
```

## Deployment

Pushes to `main` run `.github/workflows/deploy.yml`: backend tests (`pytest tests/`), frontend tests (`npm run test:run`), then deploy to AWS (`us-east-1`) with CDK from `infra/`. See [`infra/CLAUDE.md`](infra/CLAUDE.md).

## Documentation and Workflow

This project uses [SpecOps](https://github.com/tyevans/spec-ops) (project management as code). Specs, backlog, user stories, and ADRs live under `docs/project/` and are configured in `specops.toml`. CI runs `spec-ops health` (including the 500-line file limit) and `spec-ops health --numbering`; `deploy-pages.yml` builds the docs site with `spec-ops docs build`. See `AGENTS.md` for the agent operating manual and `docs/contributing.md` for contributing.

- `docs/project/product/` - PRDs (idea, shaped, accepted, shipped)
- `docs/project/backlog/` - Tasks, `PRIORITY.md`, `ROADMAP.md`
- `docs/project/user_stories/` - Personas and Gherkin user stories
- `docs/project/adrs/` - Architecture decision records
- `docs/project/archive/docs/` - Legacy docs (features, architecture, API spec, design system, frontend requirements, API/frontend contracts)

Component guides: [`app/CLAUDE.md`](app/CLAUDE.md), [`frontend/CLAUDE.md`](frontend/CLAUDE.md), [`infra/CLAUDE.md`](infra/CLAUDE.md).
