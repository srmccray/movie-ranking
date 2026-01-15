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

const TOKEN_KEY = 'movie_ranking_token';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Initialize auth state from localStorage
  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_KEY);
    if (storedToken) {
      setToken(storedToken);
      apiClient.setToken(storedToken);
    }
    setIsLoading(false);
  }, []);

  const saveToken = useCallback((newToken: string) => {
    localStorage.setItem(TOKEN_KEY, newToken);
    setToken(newToken);
    apiClient.setToken(newToken);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      try {
        const response = await apiClient.login(email, password);
        saveToken(response.access_token);
      } catch (error) {
        if (error instanceof ApiClientError) {
          throw error;
        }
        throw new Error('Failed to login. Please try again.');
      }
    },
    [saveToken]
  );

  const register = useCallback(
    async (email: string, password: string) => {
      try {
        const response = await apiClient.register(email, password);
        saveToken(response.access_token);
      } catch (error) {
        if (error instanceof ApiClientError) {
          throw error;
        }
        throw new Error('Failed to register. Please try again.');
      }
    },
    [saveToken]
  );

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    apiClient.setToken(null);
  }, []);

  const loginWithToken = useCallback(
    (accessToken: string) => {
      saveToken(accessToken);
    },
    [saveToken]
  );

  const value: AuthContextType = {
    token,
    isAuthenticated: !!token,
    isLoading,
    login,
    register,
    logout,
    loginWithToken,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
