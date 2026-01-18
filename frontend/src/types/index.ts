// API Response Types

export interface Token {
  access_token: string;
  token_type: string;
}

// Google OAuth Types
export interface GoogleAuthUrlResponse {
  authorization_url: string;
}

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
export interface UserProfileResponse {
  id: string;
  email: string;
  auth_provider: 'local' | 'google' | 'linked';
  has_google_linked: boolean;
  has_password: boolean;
  created_at: string;
}

export interface Movie {
  id: string;
  title: string;
  year: number | null;
  tmdb_id?: number | null;
  poster_url?: string | null;
  genre_ids?: number[] | null;
  vote_average?: number | null;
  vote_count?: number | null;
  release_date?: string | null;
  original_language?: string | null;
  runtime?: number | null;
  created_at: string;
}

export interface MovieBrief {
  id: string;
  title: string;
  year: number | null;
  tmdb_id?: number | null;
  poster_url?: string | null;
  genre_ids?: number[] | null;
}

export interface TMDBSearchResult {
  tmdb_id: number;
  title: string;
  year: number | null;
  poster_url: string | null;
  overview: string | null;
  genre_ids?: number[] | null;
  vote_average?: number | null;
  vote_count?: number | null;
  release_date?: string | null;
  original_language?: string | null;
}

export interface Ranking {
  id: string;
  movie_id: string;
  rating: number;
  rated_at: string;
  created_at: string;
  updated_at: string;
}

export interface RankingWithMovie {
  id: string;
  rating: number;
  rated_at: string;
  created_at: string;
  updated_at: string;
  movie: MovieBrief;
}

export interface RankingListResponse {
  items: RankingWithMovie[];
  total: number;
  limit: number;
  offset: number;
}

// Sort types
export type SortField = 'rated_at' | 'rating' | 'title' | 'year';
export type SortOrder = 'asc' | 'desc';

export interface SortOption {
  label: string;
  field: SortField;
  order: SortOrder;
}

// Analytics types
export interface ActivityDay {
  date: string;
  count: number;
}

export interface ActivityResponse {
  activity: ActivityDay[];
  start_date: string;
  end_date: string;
}

export interface GenreStats {
  genre_id: number;
  genre_name: string;
  count: number;
  average_rating: number;
}

export interface GenreResponse {
  genres: GenreStats[];
  total_movies: number;
}

export interface StatsResponse {
  total_movies: number;
  total_watch_time_minutes: number;
  average_rating: number;
  current_streak: number;
  longest_streak: number;
  top_genre: string | null;
}

export interface RatingCount {
  rating: number;
  count: number;
}

export interface RatingDistributionResponse {
  distribution: RatingCount[];
  total: number;
}

// Request Types

export interface UserCreate {
  email: string;
  password: string;
}

export interface MovieCreate {
  title: string;
  year?: number | null;
  tmdb_id?: number | null;
  poster_url?: string | null;
  genre_ids?: number[] | null;
  vote_average?: number | null;
  vote_count?: number | null;
  release_date?: string | null;
  original_language?: string | null;
  runtime?: number | null;
}

export interface RankingCreate {
  movie_id: string;
  rating: number;
  rated_at?: string;
}

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
export interface ParsedMovieItem {
  title: string;
  watch_date: string | null;  // ISO 8601 or null
  prime_image_url: string | null;
}

/**
 * TMDB search result for import matching.
 */
export interface TMDBMatchResult {
  tmdb_id: number;
  title: string;
  year: number | null;
  poster_url: string | null;
  overview: string | null;
  genre_ids?: number[] | null;
  vote_average?: number | null;
  vote_count?: number | null;
  release_date?: string | null;
  original_language?: string | null;
}

/**
 * A parsed movie with TMDB match results.
 */
export interface MatchedMovieItem {
  parsed: ParsedMovieItem;
  tmdb_match: TMDBMatchResult | null;
  confidence: number;  // 0.0 - 1.0
  alternatives: TMDBMatchResult[];
  status: 'pending' | 'added' | 'skipped';
}

/**
 * Response after uploading Amazon Prime CSV file.
 * POST /api/v1/import/amazon-prime/upload/
 */
export interface ImportSessionResponse {
  session_id: string;
  total_entries: number;
  movies_found: number;
  tv_shows_filtered: number;
  already_ranked: number;
  ready_for_review: number;
  movies: MatchedMovieItem[];
}

/**
 * Current import session state.
 * GET /api/v1/import/amazon-prime/session/{session_id}/
 */
export interface ImportSessionDetailResponse {
  session_id: string;
  current_index: number;
  total_movies: number;
  added_count: number;
  skipped_count: number;
  remaining_count: number;
  movies: MatchedMovieItem[];
}

/**
 * Request to add a movie from import session.
 * POST /api/v1/import/amazon-prime/session/{session_id}/movie/{index}/add/
 */
export interface ImportMovieAddRequest {
  rating: number;  // 1-5
  rated_at?: string | null;  // ISO 8601, optional
}

/**
 * Request to update a movie's TMDB match in an import session.
 * PATCH /api/v1/import/amazon-prime/session/{session_id}/movie/{index}/match/
 */
export interface ImportMovieMatchRequest {
  tmdb_id: number;
  title: string;
  year?: number | null;
  poster_url?: string | null;
  overview?: string | null;
  genre_ids?: number[] | null;
  vote_average?: number | null;
  vote_count?: number | null;
  release_date?: string | null;
  original_language?: string | null;
}

/**
 * Summary after completing import (computed from session state).
 */
export interface ImportCompletionSummary {
  movies_added: number;
  movies_skipped: number;
  unmatched_titles: string[];
}
