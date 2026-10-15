/**
 * MSW request handlers for mocking API endpoints in tests.
 *
 * These handlers simulate the backend API behavior for:
 * - Authentication (login, register)
 * - Movies (create, search)
 * - Rankings (list, create)
 *
 * Split by domain: state.ts (mock data and helpers), auth.ts, movies.ts, import.ts.
 */

import { authHandlers } from './auth';
import { movieHandlers } from './movies';

export const handlers = [...authHandlers, ...movieHandlers];

export { importHandlers, resetImportSessions, createMockImportSession, MOCK_IMPORT_SESSION } from './import';
export {
  resetMockData,
  setTmdbServiceError,
  addValidOAuthState,
  setUserGoogleLinked,
  MOCK_TOKEN,
  MOCK_USER_EMAIL,
  MOCK_USER_PASSWORD,
  MOCK_TMDB_RESULTS,
  MOCK_GOOGLE_STATE,
  MOCK_GOOGLE_AUTH_URL,
} from './state';
