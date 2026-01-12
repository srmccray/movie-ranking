# API-Frontend Contract Verification

## Overview

This document verifies the compatibility between the backend API and the frontend implementation.

## Endpoint Contracts

### Authentication

#### POST /api/v1/auth/register

**Backend Contract:**
- Request Body: `{ email: string, password: string }` (JSON)
- Response: `{ access_token: string, token_type: "bearer" }`
- Status Codes: 201 (success), 409 (email exists), 422 (validation error)

**Frontend Implementation:**
- File: `frontend/src/api/client.ts` - `register()` method
- Sends JSON body with email and password
- Stores returned token in localStorage via AuthContext

**Status: COMPATIBLE**

---

#### POST /api/v1/auth/login

**Backend Contract:**
- Request Body: Form-encoded (`username=email&password=pwd`)
- Content-Type: `application/x-www-form-urlencoded`
- Response: `{ access_token: string, token_type: "bearer" }`
- Status Codes: 200 (success), 401 (invalid credentials)

**Frontend Implementation:**
- File: `frontend/src/api/client.ts` - `login()` method
- Uses URLSearchParams to send form-encoded data
- Sets Content-Type to `application/x-www-form-urlencoded`
- Note: OAuth2 form uses `username` field (not `email`)

**Status: COMPATIBLE**

---

### Movies

#### POST /api/v1/movies

**Backend Contract:**
- Request Body: `{ title: string, year?: number | null }` (JSON)
- Headers: `Authorization: Bearer <token>`
- Response: `{ id: UUID, title: string, year?: number, created_at: datetime }`
- Status Codes: 201 (success), 401 (unauthorized), 422 (validation error)
- Validation: title 1-500 chars, year 1888-2031

**Frontend Implementation:**
- File: `frontend/src/api/client.ts` - `createMovie()` method
- Sends JSON body with title and optional year
- Authorization header added automatically when token is set
- Type: `MovieCreate` matches backend schema

**Status: COMPATIBLE**

---

### Rankings

#### POST /api/v1/rankings

**Backend Contract:**
- Request Body: `{ movie_id: UUID, rating: number }` (JSON)
- Headers: `Authorization: Bearer <token>`
- Response: `{ id: UUID, movie_id: UUID, rating: number, created_at: datetime, updated_at: datetime }`
- Status Codes: 200 (updated), 201 (created), 401 (unauthorized), 404 (movie not found), 422 (validation error)
- Validation: rating 1-5

**Frontend Implementation:**
- File: `frontend/src/api/client.ts` - `createOrUpdateRanking()` method
- Sends JSON body with movie_id (string UUID) and rating
- Type: `RankingCreate` matches backend schema

**Status: COMPATIBLE**

---

#### GET /api/v1/rankings

**Backend Contract:**
- Query Params: `limit` (1-100, default 20), `offset` (>=0, default 0)
- Headers: `Authorization: Bearer <token>`
- Response:
```json
{
  "items": [
    {
      "id": "uuid",
      "rating": 5,
      "created_at": "datetime",
      "updated_at": "datetime",
      "movie": {
        "id": "uuid",
        "title": "string",
        "year": number | null
      }
    }
  ],
  "total": number,
  "limit": number,
  "offset": number
}
```
- Status Codes: 200 (success), 401 (unauthorized)

**Frontend Implementation:**
- File: `frontend/src/api/client.ts` - `getRankings()` method
- Sends limit and offset as query parameters
- Type: `RankingListResponse` matches backend schema exactly

**Status: COMPATIBLE**

---

## Type Mapping

| Backend (Pydantic) | Frontend (TypeScript) | Notes |
|-------------------|----------------------|-------|
| UUID | string | UUIDs serialized as strings in JSON |
| datetime | string | ISO 8601 format, parsed on demand |
| EmailStr | string | Validated on backend |
| int (rating 1-5) | number | Validated on both ends |
| Optional[int] | number \| null | year field |

---

## Error Handling

### Backend Error Format

Simple error:
```json
{ "detail": "Error message" }
```

Validation error (422):
```json
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

### Frontend Error Handling

- File: `frontend/src/api/client.ts` - `ApiClientError` class
- Extracts message from `detail` string or first validation error
- Preserves HTTP status code for conditional handling
- Properly handles both error formats

**Status: COMPATIBLE**

---

## CORS Configuration

**Backend:**
- File: `app/main.py`
- Allowed Origins: `["http://localhost:3000"]`
- Credentials: Allowed
- Methods: All
- Headers: All

**Frontend:**
- Dev server runs on port 3000
- Vite proxy configured for API requests
- Credentials included in requests

**Status: COMPATIBLE**

---

## Authentication Flow

1. User registers/logs in via frontend
2. Backend returns JWT token
3. Frontend stores token in localStorage
4. Frontend includes token in Authorization header for protected endpoints
5. Backend validates token via FastAPI dependency injection
6. On 401 response, frontend redirects to login

**Token Storage:**
- Key: `movie_ranking_token`
- Location: localStorage
- Set via `AuthContext` on successful auth
- Cleared on logout

**Status: COMPATIBLE**

---

## Verification Checklist

- [x] Registration endpoint compatible
- [x] Login endpoint compatible (OAuth2 form format)
- [x] Movie creation endpoint compatible
- [x] Ranking creation/update endpoint compatible
- [x] Rankings list endpoint compatible
- [x] Error response handling compatible
- [x] CORS properly configured
- [x] Authentication flow complete
- [x] Type definitions match API schemas

---

## Notes for Production

1. **Environment Variables:**
   - Backend should support configurable CORS origins
   - Frontend should use environment variable for API base URL

2. **Token Security:**
   - Consider httpOnly cookies for production
   - Implement token refresh mechanism for long sessions

3. **Rate Limiting:**
   - Backend has planned rate limits (not implemented in MVP)
   - Frontend should handle 429 responses gracefully

4. **API Versioning:**
   - All endpoints use `/api/v1` prefix
   - Frontend API client uses this prefix consistently
