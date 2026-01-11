# Movie Ranking API

A FastAPI backend for a movie ranking website. Users can register, log in, add movies, and rank them on a 1-5 scale.

## Current State

**MVP Complete** - All core features implemented and tested:

- User registration and login (JWT authentication)
- Add movies (title + optional year)
- Rank movies 1-5 (upsert behavior - re-ranking updates existing)
- List your rankings with pagination
- CORS configured for React frontend integration

## Tech Stack

- **Framework:** FastAPI
- **Database:** PostgreSQL with async SQLAlchemy 2.0
- **Migrations:** Alembic
- **Authentication:** JWT (python-jose) + bcrypt password hashing
- **Validation:** Pydantic v2
- **Containerization:** Docker + Docker Compose

## Project Structure

```
movie-ranking/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings from environment
│   ├── database.py          # Async SQLAlchemy setup
│   ├── dependencies.py      # Auth dependencies (get_current_user)
│   ├── models/              # SQLAlchemy models
│   │   ├── user.py
│   │   ├── movie.py
│   │   └── ranking.py
│   ├── schemas/             # Pydantic request/response schemas
│   ├── routers/             # API route handlers
│   │   ├── auth.py
│   │   ├── movies.py
│   │   └── rankings.py
│   └── utils/
│       └── security.py      # Password hashing, JWT utilities
├── alembic/                  # Database migrations
├── docs/                     # Product and technical documentation
├── Dockerfile                # Multi-stage build for the API
├── docker-compose.yml        # Full stack orchestration
├── .env.example              # Environment variable template
├── pyproject.toml
└── requirements.txt
```

## Quick Start with Docker

The fastest way to get the full stack running.

### Prerequisites

- Docker and Docker Compose

### Start the Application

```bash
# Copy environment template
cp .env.example .env
# Edit .env to set a secure SECRET_KEY (or use defaults for development)

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
| POSTGRES_USER | No | postgres | Database user |
| POSTGRES_PASSWORD | No | postgres | Database password |
| POSTGRES_DB | No | movie_ranking | Database name |
| POSTGRES_PORT | No | 5432 | Host port for database |
| API_PORT | No | 8000 | Host port for API |
| ALGORITHM | No | HS256 | JWT algorithm |
| ACCESS_TOKEN_EXPIRE_MINUTES | No | 1440 | Token lifetime (24 hours) |
| DEBUG | No | false | Debug mode |

Example `.env`:
```
SECRET_KEY=your-256-bit-secret-key-here
POSTGRES_PASSWORD=mysecurepassword
```

## Local Development (without Docker)

If you prefer running without Docker:

### Prerequisites

- Python 3.11+
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
# Set DATABASE_URL to your local PostgreSQL instance
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

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | No | Health check |
| POST | `/api/v1/auth/register` | No | Create account |
| POST | `/api/v1/auth/login` | No | Login (returns JWT) |
| POST | `/api/v1/movies/` | Yes | Add a movie |
| POST | `/api/v1/rankings/` | Yes | Create/update ranking |
| GET | `/api/v1/rankings/` | Yes | List your rankings |

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
# With Docker
docker compose exec api pytest

# Without Docker
pip install pytest pytest-asyncio httpx
pytest
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

## Documentation

Detailed documentation is available in the `/docs` folder:

- `features.md` - Product requirements and user stories
- `architecture.md` - Technical architecture and design decisions
- `api-spec.md` - Complete API specification with examples
