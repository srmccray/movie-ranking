/**
 * Shared mutable mock state, constants and reset/setter helpers for the MSW handlers.
 * The reassigned `let` variables live here so only this module assigns them;
 * other modules read them through ES module live bindings.
 */

import { importSessions } from './import';

// Mock data
export const MOCK_TOKEN = 'mock-jwt-token-for-testing';  // pragma: allowlist secret
export const MOCK_USER_EMAIL = 'test@example.com';
export const MOCK_USER_PASSWORD = 'password123';

// Mock TMDB search results
export const MOCK_TMDB_RESULTS = [
  {
    tmdb_id: 603,
    title: 'The Matrix',
    year: 1999,
    poster_url: 'https://image.tmdb.org/t/p/w185/abc123.jpg',
    overview: 'A computer hacker learns about the true nature of reality.',
    genre_ids: [28, 878],
    vote_average: 8.7,
    vote_count: 24000,
    release_date: '1999-03-30',
    original_language: 'en',
  },
  {
    tmdb_id: 604,
    title: 'The Matrix Reloaded',
    year: 2003,
    poster_url: 'https://image.tmdb.org/t/p/w185/def456.jpg',
    overview: 'Neo continues his mission to save humanity.',
    genre_ids: [28, 878],
    vote_average: 7.0,
    vote_count: 12000,
    release_date: '2003-05-15',
    original_language: 'en',
  },
  {
    tmdb_id: 605,
    title: 'The Matrix Revolutions',
    year: 2003,
    poster_url: 'https://image.tmdb.org/t/p/w185/ghi789.jpg',
    overview: 'The epic conclusion to the Matrix trilogy.',
    genre_ids: [28, 878],
    vote_average: 6.7,
    vote_count: 10000,
    release_date: '2003-11-05',
    original_language: 'en',
  },
];

// Store registered users for testing
export const registeredUsers = new Map<string, string>();
registeredUsers.set(MOCK_USER_EMAIL, MOCK_USER_PASSWORD);

// Mock Google OAuth state
export const MOCK_GOOGLE_STATE = 'mock-google-oauth-state-123';
export const MOCK_GOOGLE_AUTH_URL = `https://accounts.google.com/o/oauth2/v2/auth?client_id=test&redirect_uri=http://localhost:8000/api/v1/auth/google/callback/&response_type=code&scope=openid%20email%20profile&state=${MOCK_GOOGLE_STATE}`;

// Store valid states for testing
export const validOAuthStates = new Set<string>();
validOAuthStates.add(MOCK_GOOGLE_STATE);

// Store link states (for account linking flow)
export const validLinkStates = new Set<string>();

// Track if user has Google linked
export let userHasGoogleLinked = false;

// Store movies for testing
export const movies = new Map<string, { id: string; title: string; year: number | null; tmdb_id?: number | null; poster_url?: string | null }>();

// Store rankings for testing
export const rankings = new Map<string, { id: string; movie_id: string; rating: number }>();

// Flag to simulate TMDB service errors
export let tmdbServiceError: 'rate_limit' | 'api_error' | 'unavailable' | null = null;

// Helper to reset mock data between tests
export function resetMockData() {
  registeredUsers.clear();
  registeredUsers.set(MOCK_USER_EMAIL, MOCK_USER_PASSWORD);
  movies.clear();
  rankings.clear();
  tmdbServiceError = null;
  validOAuthStates.clear();
  validOAuthStates.add(MOCK_GOOGLE_STATE);
  validLinkStates.clear();
  userHasGoogleLinked = false;
  importSessions.clear();
}

// Helper to simulate TMDB service errors
export function setTmdbServiceError(error: 'rate_limit' | 'api_error' | 'unavailable' | null) {
  tmdbServiceError = error;
}

// Helper to add a valid OAuth state for testing
export function addValidOAuthState(state: string) {
  validOAuthStates.add(state);
}

// Helper to set Google linked status for testing
export function setUserGoogleLinked(linked: boolean) {
  userHasGoogleLinked = linked;
}
