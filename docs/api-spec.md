# Movie Ranking API - API Specification

## Overview

RESTful API specification for the Movie Ranking MVP. All endpoints return JSON responses.

**Base URL:** `/api/v1`

**Authentication:** JWT Bearer Token (where required)

---

## Authentication

Protected endpoints require the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Tokens are obtained via `/auth/register` or `/auth/login` endpoints.

---

## Endpoints Summary

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | /auth/register | No | Create new user account |
| POST | /auth/login | No | Authenticate and get token |
| POST | /movies | Yes | Add a new movie |
| POST | /rankings | Yes | Create or update a ranking |
| GET | /rankings | Yes | List user's rankings |

---

## Endpoint Specifications

### POST /auth/register

Create a new user account and return an access token.

#### Request

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Request Body:**

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| email | string | Yes | Valid email format | User's email address |
| password | string | Yes | Min 8 characters | User's password |

#### Responses

**201 Created** - Account created successfully

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**400 Bad Request** - Invalid email format

```json
{
  "detail": "Invalid email format"
}
```

**409 Conflict** - Email already registered

```json
{
  "detail": "Email already registered"
}
```

**422 Unprocessable Entity** - Validation error

```json
{
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "Password must be at least 8 characters",
      "type": "value_error"
    }
  ]
}
```

---

### POST /auth/login

Authenticate user and return an access token.

#### Request

```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=securepassword123
```

**Note:** Uses OAuth2 password flow format. The `username` field contains the email.

**Request Body (form data):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| username | string | Yes | User's email address |
| password | string | Yes | User's password |

#### Responses

**200 OK** - Login successful

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**401 Unauthorized** - Invalid credentials

```json
{
  "detail": "Invalid email or password"
}
```

---

### POST /movies

Add a new movie to the database.

#### Request

```http
POST /api/v1/movies
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "title": "The Shawshank Redemption",
  "year": 1994
}
```

**Request Body:**

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| title | string | Yes | Non-empty, max 500 chars | Movie title |
| year | integer | No | 1888-2031 | Release year |

#### Responses

**201 Created** - Movie created successfully

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "The Shawshank Redemption",
  "year": 1994,
  "created_at": "2024-01-10T12:00:00Z"
}
```

**401 Unauthorized** - Missing or invalid token

```json
{
  "detail": "Not authenticated"
}
```

**422 Unprocessable Entity** - Validation error

```json
{
  "detail": [
    {
      "loc": ["body", "year"],
      "msg": "Year must be between 1888 and 2031",
      "type": "value_error"
    }
  ]
}
```

---

### POST /rankings

Create or update a ranking for a movie. If the user has already ranked this movie, the rating is updated.

#### Request

```http
POST /api/v1/rankings
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "movie_id": "550e8400-e29b-41d4-a716-446655440000",
  "rating": 5
}
```

**Request Body:**

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| movie_id | string (UUID) | Yes | Valid UUID | ID of movie to rank |
| rating | integer | Yes | 1-5 | Rating value |

#### Responses

**201 Created** - Ranking created (new ranking)

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "movie_id": "550e8400-e29b-41d4-a716-446655440000",
  "rating": 5,
  "created_at": "2024-01-10T12:00:00Z",
  "updated_at": "2024-01-10T12:00:00Z"
}
```

**200 OK** - Ranking updated (existing ranking)

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "movie_id": "550e8400-e29b-41d4-a716-446655440000",
  "rating": 4,
  "created_at": "2024-01-10T12:00:00Z",
  "updated_at": "2024-01-10T14:30:00Z"
}
```

**401 Unauthorized** - Missing or invalid token

```json
{
  "detail": "Not authenticated"
}
```

**404 Not Found** - Movie does not exist

```json
{
  "detail": "Movie not found"
}
```

**422 Unprocessable Entity** - Validation error

```json
{
  "detail": [
    {
      "loc": ["body", "rating"],
      "msg": "Rating must be between 1 and 5",
      "type": "value_error"
    }
  ]
}
```

---

### GET /rankings

List all movies the authenticated user has ranked.

#### Request

```http
GET /api/v1/rankings?limit=20&offset=0
Authorization: Bearer <access_token>
```

**Query Parameters:**

| Parameter | Type | Required | Default | Constraints | Description |
|-----------|------|----------|---------|-------------|-------------|
| limit | integer | No | 20 | 1-100 | Number of results to return |
| offset | integer | No | 0 | >= 0 | Number of results to skip |

#### Responses

**200 OK** - Rankings retrieved successfully

```json
{
  "items": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "rating": 5,
      "created_at": "2024-01-10T12:00:00Z",
      "updated_at": "2024-01-10T12:00:00Z",
      "movie": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "title": "The Shawshank Redemption",
        "year": 1994
      }
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440002",
      "rating": 4,
      "created_at": "2024-01-09T10:00:00Z",
      "updated_at": "2024-01-09T10:00:00Z",
      "movie": {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "title": "The Godfather",
        "year": 1972
      }
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| items | array | List of ranking objects with movie details |
| total | integer | Total number of rankings for this user |
| limit | integer | Number of results requested |
| offset | integer | Number of results skipped |

**Empty Response:**

```json
{
  "items": [],
  "total": 0,
  "limit": 20,
  "offset": 0
}
```

**401 Unauthorized** - Missing or invalid token

```json
{
  "detail": "Not authenticated"
}
```

---

## Pydantic Schemas

### Request Schemas

```python
# schemas/user.py
from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)

class UserLogin(BaseModel):
    username: str  # email
    password: str
```

```python
# schemas/movie.py
from pydantic import BaseModel, Field
from typing import Optional

class MovieCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    year: Optional[int] = Field(None, ge=1888, le=2031)
```

```python
# schemas/ranking.py
from pydantic import BaseModel, Field
from uuid import UUID

class RankingCreate(BaseModel):
    movie_id: UUID
    rating: int = Field(..., ge=1, le=5)
```

### Response Schemas

```python
# schemas/token.py
from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

```python
# schemas/movie.py
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class MovieResponse(BaseModel):
    id: UUID
    title: str
    year: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True

class MovieBrief(BaseModel):
    id: UUID
    title: str
    year: Optional[int]

    class Config:
        from_attributes = True
```

```python
# schemas/ranking.py
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import List

class RankingResponse(BaseModel):
    id: UUID
    movie_id: UUID
    rating: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class RankingWithMovie(BaseModel):
    id: UUID
    rating: int
    created_at: datetime
    updated_at: datetime
    movie: MovieBrief

    class Config:
        from_attributes = True

class RankingListResponse(BaseModel):
    items: List[RankingWithMovie]
    total: int
    limit: int
    offset: int
```

---

## Error Response Schema

All error responses follow this structure:

```python
# Simple error
{
    "detail": "Error message"
}

# Validation error (422)
{
    "detail": [
        {
            "loc": ["body", "field_name"],
            "msg": "Error description",
            "type": "error_type"
        }
    ]
}
```

---

## CORS Configuration

For React frontend compatibility:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## OpenAPI Documentation

FastAPI automatically generates OpenAPI documentation at:

- **Swagger UI:** `/docs`
- **ReDoc:** `/redoc`
- **OpenAPI JSON:** `/openapi.json`

---

## Rate Limits (Future)

Not implemented in MVP, but planned structure:

| Endpoint | Limit |
|----------|-------|
| POST /auth/* | 5 requests/minute |
| POST /movies | 30 requests/minute |
| POST /rankings | 60 requests/minute |
| GET /rankings | 120 requests/minute |

---

## Example Usage

### Complete User Flow

```bash
# 1. Register a new user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepassword123"}'

# Response: {"access_token": "eyJ...", "token_type": "bearer"}

# 2. Store the token
TOKEN="eyJ..."

# 3. Add a movie
curl -X POST http://localhost:8000/api/v1/movies \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Inception", "year": 2010}'

# Response: {"id": "550e...", "title": "Inception", "year": 2010, ...}

# 4. Rank the movie
curl -X POST http://localhost:8000/api/v1/rankings \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"movie_id": "550e...", "rating": 5}'

# Response: {"id": "660e...", "movie_id": "550e...", "rating": 5, ...}

# 5. List your rankings
curl -X GET "http://localhost:8000/api/v1/rankings?limit=10" \
  -H "Authorization: Bearer $TOKEN"

# Response: {"items": [...], "total": 1, "limit": 10, "offset": 0}
```

---

## Testing Checklist

### Auth Endpoints
- [ ] Register with valid email/password returns 201 + token
- [ ] Register with invalid email returns 400
- [ ] Register with short password returns 422
- [ ] Register with existing email returns 409
- [ ] Login with valid credentials returns 200 + token
- [ ] Login with invalid password returns 401
- [ ] Login with non-existent email returns 401

### Movies Endpoints
- [ ] Create movie with valid data returns 201
- [ ] Create movie without auth returns 401
- [ ] Create movie without title returns 422
- [ ] Create movie with invalid year returns 422

### Rankings Endpoints
- [ ] Create ranking returns 201
- [ ] Update existing ranking returns 200
- [ ] Rank non-existent movie returns 404
- [ ] Invalid rating (0, 6, "five") returns 422
- [ ] List rankings returns paginated results
- [ ] List rankings without auth returns 401
- [ ] Empty rankings list returns empty array
