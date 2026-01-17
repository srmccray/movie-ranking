# Movie Ranking API - Technical Architecture

## Overview

This document defines the technical architecture for the Movie Ranking API MVP, including database schema, project structure, and key technical decisions.

---

## Technology Stack

| Layer | Technology | Version | Rationale |
|-------|------------|---------|-----------|
| Framework | FastAPI | 0.109+ | Async support, automatic OpenAPI docs, Pydantic validation |
| Database | PostgreSQL | 16+ | Robust, excellent JSON support, production-ready |
| ORM | SQLAlchemy | 2.0+ | Type-safe, async support, mature ecosystem |
| Migrations | Alembic | 1.13+ | Standard for SQLAlchemy projects |
| Auth | python-jose | 3.3+ | JWT encoding/decoding |
| Password | passlib[bcrypt] | 1.7+ | Secure password hashing |
| Validation | Pydantic | 2.5+ | FastAPI native, excellent validation |
| Server | Uvicorn | 0.27+ | ASGI server, async support |

---

## Database Schema

### Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│     users       │       │    rankings     │       │     movies      │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │───┐   │ id (PK)         │   ┌───│ id (PK)         │
│ email           │   └──>│ user_id (FK)    │   │   │ title           │
│ hashed_password │       │ movie_id (FK)   │<──┘   │ year            │
│ created_at      │       │ rating          │       │ created_at      │
│ updated_at      │       │ created_at      │       │ updated_at      │
└─────────────────┘       │ updated_at      │       └─────────────────┘
                          └─────────────────┘
```

### Table Definitions

#### users
Stores registered user accounts.

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
```

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, auto-generated | Unique user identifier |
| email | VARCHAR(255) | NOT NULL, UNIQUE | User's email address |
| hashed_password | VARCHAR(255) | NOT NULL | bcrypt-hashed password |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Account creation time |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | Last update time |

#### movies
Stores movie information added by users.

```sql
CREATE TABLE movies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    year INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_year CHECK (year IS NULL OR (year >= 1888 AND year <= 2031))
);

CREATE INDEX idx_movies_title ON movies(title);
CREATE INDEX idx_movies_year ON movies(year);
```

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, auto-generated | Unique movie identifier |
| title | VARCHAR(500) | NOT NULL | Movie title |
| year | INTEGER | CHECK 1888-2031 | Release year (optional) |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Record creation time |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | Last update time |

#### rankings
Stores user rankings for movies.

```sql
CREATE TABLE rankings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    movie_id UUID NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_movie UNIQUE (user_id, movie_id),
    CONSTRAINT chk_rating CHECK (rating >= 1 AND rating <= 5)
);

CREATE INDEX idx_rankings_user_id ON rankings(user_id);
CREATE INDEX idx_rankings_movie_id ON rankings(movie_id);
CREATE INDEX idx_rankings_user_updated ON rankings(user_id, updated_at DESC);
```

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, auto-generated | Unique ranking identifier |
| user_id | UUID | FK -> users.id, NOT NULL | User who made the ranking |
| movie_id | UUID | FK -> movies.id, NOT NULL | Movie being ranked |
| rating | INTEGER | NOT NULL, CHECK 1-5 | Rating value |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Initial ranking time |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | Last rating update time |

**Constraints:**
- `UNIQUE (user_id, movie_id)` - One ranking per user per movie
- `ON DELETE CASCADE` - Rankings deleted when user/movie deleted

---

## Project Structure

```
movie-ranking/
├── docs/                          # Documentation
│   ├── features.md               # Product requirements
│   ├── architecture.md           # This file
│   └── api-spec.md               # API specification
├── app/                           # Application code
│   ├── __init__.py
│   ├── main.py                   # FastAPI application entry point
│   ├── config.py                 # Configuration management
│   ├── database.py               # Database connection setup
│   ├── dependencies.py           # Shared dependencies (get_db, get_current_user)
│   ├── models/                   # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── movie.py
│   │   └── ranking.py
│   ├── schemas/                  # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── movie.py
│   │   ├── ranking.py
│   │   └── token.py
│   ├── routers/                  # API route handlers
│   │   ├── __init__.py
│   │   ├── auth.py               # /auth endpoints
│   │   ├── movies.py             # /movies endpoints
│   │   └── rankings.py           # /rankings endpoints
│   ├── services/                 # Business logic
│   │   ├── __init__.py
│   │   ├── auth.py               # Authentication service
│   │   ├── movie.py              # Movie service
│   │   └── ranking.py            # Ranking service
│   └── utils/                    # Utilities
│       ├── __init__.py
│       └── security.py           # Password hashing, JWT utils
├── alembic/                       # Database migrations
│   ├── versions/
│   ├── env.py
│   └── alembic.ini
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── conftest.py               # Pytest fixtures
│   ├── test_auth.py
│   ├── test_movies.py
│   └── test_rankings.py
├── .env.example                   # Environment variable template
├── .gitignore
├── pyproject.toml                 # Project dependencies (Poetry/pip)
├── requirements.txt               # Pip requirements
└── README.md
```

---

## Authentication Architecture

### JWT Token Flow

```
┌─────────┐         ┌─────────┐         ┌─────────┐
│ Client  │         │   API   │         │   DB    │
└────┬────┘         └────┬────┘         └────┬────┘
     │                   │                   │
     │ POST /auth/register                   │
     │ {email, password} │                   │
     │──────────────────>│                   │
     │                   │ INSERT user       │
     │                   │──────────────────>│
     │                   │      user_id      │
     │                   │<──────────────────│
     │   {access_token}  │                   │
     │<──────────────────│                   │
     │                   │                   │
     │ POST /auth/login  │                   │
     │ {email, password} │                   │
     │──────────────────>│                   │
     │                   │ SELECT user       │
     │                   │──────────────────>│
     │                   │      user         │
     │                   │<──────────────────│
     │                   │ verify password   │
     │   {access_token}  │                   │
     │<──────────────────│                   │
     │                   │                   │
     │ GET /rankings     │                   │
     │ Authorization:    │                   │
     │ Bearer <token>    │                   │
     │──────────────────>│                   │
     │                   │ decode & verify   │
     │                   │ JWT token         │
     │                   │ SELECT rankings   │
     │                   │──────────────────>│
     │                   │    rankings       │
     │                   │<──────────────────│
     │    [rankings]     │                   │
     │<──────────────────│                   │
```

### JWT Token Structure

```json
{
  "sub": "user-uuid-here",
  "exp": 1704931200,
  "iat": 1704844800,
  "type": "access"
}
```

| Claim | Description |
|-------|-------------|
| sub | User ID (UUID) |
| exp | Expiration timestamp (24h from issue) |
| iat | Issued at timestamp |
| type | Token type ("access") |

### Security Configuration

```python
# Environment variables
SECRET_KEY=<random-256-bit-key>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24 hours
```

---

## Configuration Management

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| DATABASE_URL | Yes | - | PostgreSQL connection string |
| SECRET_KEY | Yes | - | JWT signing key (256-bit) |
| ALGORITHM | No | HS256 | JWT algorithm |
| ACCESS_TOKEN_EXPIRE_MINUTES | No | 1440 | Token lifetime |
| DEBUG | No | False | Debug mode |

### Example .env

```bash
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/movie_ranking
SECRET_KEY=your-256-bit-secret-key-here-keep-it-safe
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
DEBUG=False
```

---

## Error Handling Strategy

### Standard Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### HTTP Status Code Usage

| Code | Usage |
|------|-------|
| 200 | Successful GET, PUT |
| 201 | Successful POST (resource created) |
| 400 | Invalid request format |
| 401 | Missing or invalid authentication |
| 404 | Resource not found |
| 409 | Conflict (e.g., duplicate email) |
| 422 | Validation error (invalid data) |
| 500 | Internal server error |

---

## Key Technical Decisions

### ADR-001: UUID Primary Keys
**Decision:** Use UUIDs instead of auto-incrementing integers for primary keys.

**Rationale:**
- No ID enumeration vulnerability
- Safe for distributed systems (future-proofing)
- Can generate IDs client-side if needed

**Tradeoffs:**
- Slightly larger storage (16 bytes vs 4-8)
- Less human-readable

---

### ADR-002: Async SQLAlchemy
**Decision:** Use SQLAlchemy 2.0 with async support.

**Rationale:**
- Better performance under concurrent load
- Native FastAPI async compatibility
- Modern SQLAlchemy patterns

**Tradeoffs:**
- Slightly more complex session management
- Some SQLAlchemy features require sync context

---

### ADR-003: Upsert for Rankings
**Decision:** Rankings use upsert (insert or update) behavior.

**Rationale:**
- Simpler API (single endpoint for create/update)
- Matches user mental model (set my rating)
- Avoids "already rated" error handling

**Implementation:**
```python
# PostgreSQL ON CONFLICT
INSERT INTO rankings (user_id, movie_id, rating)
VALUES ($1, $2, $3)
ON CONFLICT (user_id, movie_id)
DO UPDATE SET rating = $3, updated_at = NOW()
```

---

### ADR-004: Global Movie Pool
**Decision:** Movies are shared globally, not per-user.

**Rationale:**
- Enables future features (average ratings, discovery)
- Reduces data duplication
- Matches common movie database patterns

**Tradeoffs:**
- Cannot have user-specific movie metadata
- Need moderation strategy for v2+

---

## Performance Considerations

### Database Indexes
- `users.email` - Fast login lookups
- `rankings.user_id` - Fast user rankings retrieval
- `rankings(user_id, updated_at DESC)` - Efficient sorted listing

### Connection Pooling
- Use SQLAlchemy async pool with reasonable limits
- Default: min=5, max=20 connections

### Query Optimization
- Use `joinedload` for ranking queries (include movie data)
- Paginate all list endpoints
- No N+1 queries

---

## Security Considerations

1. **Password Storage:** bcrypt with cost factor 12
2. **JWT Secrets:** Minimum 256-bit random key
3. **SQL Injection:** Prevented by SQLAlchemy parameterization
4. **Input Validation:** Pydantic validates all inputs
5. **CORS:** Configure for React frontend domain
6. **Rate Limiting:** Consider for v2 (not MVP)
