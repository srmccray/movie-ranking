import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react';
import { apiClient, ApiClientError } from '../api/client';
import type { AuthContextType } from '../types';

const AuthContext = createContext<AuthContextType | null>(null);

/** Key the pre-cookie build stored its JWT under; removed once on startup. */
const LEGACY_TOKEN_KEY = 'movie_ranking_token';

/**
 * Provides cookie-session auth state (ADR-0013).
 *
 * The session JWT lives in an httpOnly cookie that page scripts cannot read, so
 * signed-in state is learned from `GET /auth/me/` rather than from storage.
 * Nothing token-like is ever persisted by the SPA.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Clear local state on logout or when any API call returns 401 (US-0003).
  const clearSession = useCallback(() => {
    setIsAuthenticated(false);
  }, []);

  // On any API 401 (US-0003) drop local state and ask the server to expire the
  // httpOnly cookies, which page scripts cannot remove themselves.
  const handleUnauthorized = useCallback(() => {
    clearSession();
    apiClient.logout().catch(() => {
      // Best effort: the local state is already cleared.
    });
  }, [clearSession]);

  // Register before the initial /auth/me/ call so a 401 there is handled too.
  useEffect(() => {
    apiClient.setOnUnauthorized(handleUnauthorized);
    return () => {
      apiClient.setOnUnauthorized(null);
    };
  }, [handleUnauthorized]);

  /** Ask the server whether the session cookie is valid. Resolves true if so. */
  const refreshAuth = useCallback(async (): Promise<boolean> => {
    try {
      await apiClient.getCurrentUser();
      setIsAuthenticated(true);
      return true;
    } catch {
      setIsAuthenticated(false);
      return false;
    }
  }, []);

  useEffect(() => {
    // One-time cleanup of the token the previous build kept in localStorage.
    try {
      localStorage.removeItem(LEGACY_TOKEN_KEY);
    } catch {
      // Storage may be unavailable (private mode); nothing to clean up then.
    }

    let cancelled = false;
    void refreshAuth().finally(() => {
      if (!cancelled) setIsLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [refreshAuth]);

  const login = useCallback(
    async (email: string, password: string) => {
      try {
        await apiClient.login(email, password);
      } catch (error) {
        if (error instanceof ApiClientError) {
          throw error;
        }
        throw new Error('Failed to login. Please try again.', { cause: error });
      }
      if (!(await refreshAuth())) {
        throw new Error('Failed to login. Please try again.');
      }
    },
    [refreshAuth]
  );

  const register = useCallback(
    async (email: string, password: string) => {
      try {
        await apiClient.register(email, password);
      } catch (error) {
        if (error instanceof ApiClientError) {
          throw error;
        }
        throw new Error('Failed to register. Please try again.', { cause: error });
      }
      if (!(await refreshAuth())) {
        throw new Error('Failed to register. Please try again.');
      }
    },
    [refreshAuth]
  );

  const logout = useCallback(async () => {
    try {
      await apiClient.logout();
    } catch {
      // Even if the request fails, drop the local signed-in state.
    }
    clearSession();
  }, [clearSession]);

  const value: AuthContextType = {
    isAuthenticated,
    isLoading,
    login,
    register,
    logout,
    refreshAuth,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// The hook is deliberately co-located with its provider; moving it would change
// every importer for no runtime benefit (fast refresh only affects dev reloads).
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
