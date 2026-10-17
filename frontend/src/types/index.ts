import type { components } from '@/api/.generated/schema';

// API-shaped types alias the generated OpenAPI schema (ADR-0012); do not hand-copy fields.
type Schemas = components['schemas'];

// API Response Types

export type Token = Schemas['Token'];

// Google OAuth Types
export type GoogleAuthUrlResponse = Schemas['GoogleAuthUrlResponse'];

export interface GoogleCallbackError {
  error: string;
  error_description?: string;
}

export interface AccountLinkingResponse {
  requires_linking: boolean;
  email: string;
  message: string;
}

// User Profile Types
export type UserProfileResponse = Schemas['UserProfileResponse'];

export type Movie = Schemas['MovieResponse'];

export type MovieBrief = Schemas['MovieBrief'];

export type TMDBSearchResult = Schemas['TMDBSearchResult'];

export type Ranking = Schemas['RankingResponse'];

export type RankingWithMovie = Schemas['RankingWithMovie'];

export type RankingListResponse = Schemas['RankingListResponse'];

// Sort types
export type SortField = 'rated_at' | 'rating' | 'title' | 'year';
export type SortOrder = 'asc' | 'desc';

export interface SortOption {
  label: string;
  field: SortField;
  order: SortOrder;
}

// Analytics types
export type ActivityDay = Schemas['ActivityDay'];

export type ActivityResponse = Schemas['ActivityResponse'];

export type GenreStats = Schemas['GenreStats'];

export type GenreResponse = Schemas['GenreResponse'];

export type StatsResponse = Schemas['StatsResponse'];

export type RatingCount = Schemas['RatingCount'];

export type RatingDistributionResponse = Schemas['RatingDistributionResponse'];

// Request Types

export type UserCreate = Schemas['UserCreate'];

export type MovieCreate = Schemas['MovieCreate'];

export type RankingCreate = Schemas['RankingCreate'];

// API Error Types

export interface ApiError {
  detail: string | ValidationError[];
}

export interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

// Auth Context Types

export interface AuthState {
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  loginWithToken: (token: string) => void;
}

// ============================================
// Amazon Prime Import Types
// ============================================

/**
 * A movie parsed from the Amazon Prime CSV file.
 */
export type ParsedMovieItem = Schemas['ParsedMovieItem'];

/**
 * TMDB search result for import matching.
 */
export type TMDBMatchResult = Schemas['TMDBMatchResult'];

/**
 * A parsed movie with TMDB match results.
 */
export type MatchedMovieItem = Schemas['MatchedMovieItem'];

/**
 * Response after uploading Amazon Prime CSV file.
 * POST /api/v1/import/amazon-prime/upload/
 */
export type ImportSessionResponse = Schemas['ImportSessionResponse'];

/**
 * Current import session state.
 * GET /api/v1/import/amazon-prime/session/{session_id}/
 */
export type ImportSessionDetailResponse = Schemas['ImportSessionDetailResponse'];

/**
 * Request to add a movie from import session.
 * POST /api/v1/import/amazon-prime/session/{session_id}/movie/{index}/add/
 */
export type ImportMovieAddRequest = Schemas['ImportMovieAddRequest'];

/**
 * Request to update a movie's TMDB match in an import session.
 * PATCH /api/v1/import/amazon-prime/session/{session_id}/movie/{index}/match/
 */
export type ImportMovieMatchRequest = Schemas['ImportMovieMatchRequest'];
