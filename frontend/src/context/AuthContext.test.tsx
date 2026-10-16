/**
 * Tests for AuthContext and AuthProvider.
 *
 * These tests verify:
 * - Login flow updates authentication state
 * - Register flow updates authentication state
 * - Logout clears authentication state
 * - Signed-in state comes from GET /auth/me/ (cookie session), not storage
 * - No token is ever written to localStorage; the legacy key is cleaned up
 * - Logout calls the API then clears state
 * - Error handling for failed authentication
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { AuthProvider, useAuth } from './AuthContext';
import { apiClient } from '../api/client';
import { server } from '../__tests__/mocks/server';
import { resetMockData, setMockSession, hasMockSession, MOCK_USER_EMAIL, MOCK_USER_PASSWORD } from '../__tests__/mocks/handlers';

// Test component that uses the auth context
function TestAuthConsumer() {
  const { isAuthenticated, isLoading, login, register, logout } = useAuth();

  return (
    <div>
      <div data-testid="loading">{isLoading.toString()}</div>
      <div data-testid="authenticated">{isAuthenticated.toString()}</div>
      <button onClick={() => login(MOCK_USER_EMAIL, MOCK_USER_PASSWORD)}>
        Login
      </button>
      <button onClick={() => register('new@example.com', 'password123')}>
        Register
      </button>
      <button onClick={() => void logout()}>Logout</button>
    </div>
  );
}

describe('AuthContext', () => {
  beforeEach(() => {
    localStorage.clear();
    resetMockData();
  });

  describe('AuthProvider', () => {
    it('should provide initial unauthenticated state', async () => {
      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      );

      // Wait for loading to complete
      await waitFor(() => {
        expect(screen.getByTestId('loading').textContent).toBe('false');
      });

      expect(screen.getByTestId('authenticated').textContent).toBe('false');
    });

    it('should restore signed-in state from the cookie session on mount', async () => {
      // The server recognises the session cookie
      setMockSession(true);

      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('loading').textContent).toBe('false');
      });

      expect(screen.getByTestId('authenticated').textContent).toBe('true');
    });

    it('should remove the legacy localStorage token on startup', async () => {
      localStorage.setItem('movie_ranking_token', 'old-token');

      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('loading').textContent).toBe('false');
      });

      expect(localStorage.getItem('movie_ranking_token')).toBeNull();
    });

    it('should resolve loading state after initialization', async () => {
      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      );

      // After initialization, loading should be false
      // Note: With React 18 concurrent mode and useEffect, the loading state
      // may be resolved before we can check the initial 'true' state
      await waitFor(() => {
        expect(screen.getByTestId('loading').textContent).toBe('false');
      });
    });
  });

  describe('login', () => {
    it('should update state after successful login', async () => {
      const user = userEvent.setup();

      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      );

      // Wait for loading to complete
      await waitFor(() => {
        expect(screen.getByTestId('loading').textContent).toBe('false');
      });

      // Click login button
      await user.click(screen.getByText('Login'));

      // Wait for authentication to complete
      await waitFor(() => {
        expect(screen.getByTestId('authenticated').textContent).toBe('true');
      });

    });

    it('should not write a token to localStorage after login', async () => {
      const user = userEvent.setup();

      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('loading').textContent).toBe('false');
      });

      await user.click(screen.getByText('Login'));

      await waitFor(() => {
        expect(screen.getByTestId('authenticated').textContent).toBe('true');
      });
      await waitFor(() => {
        expect(localStorage.getItem('movie_ranking_token')).toBeNull();
        expect(localStorage.length).toBe(0);
      });
    });

    it('should throw error on failed login', async () => {
      const user = userEvent.setup();
      const onError = vi.fn();

      function ErrorTestComponent() {
        const { login } = useAuth();

        const handleLogin = async () => {
          try {
            await login('bad@example.com', 'wrongpassword');
          } catch (e) {
            onError(e);
          }
        };

        return <button onClick={handleLogin}>Bad Login</button>;
      }

      render(
        <AuthProvider>
          <ErrorTestComponent />
        </AuthProvider>
      );

      await user.click(screen.getByText('Bad Login'));

      await waitFor(() => {
        expect(onError).toHaveBeenCalled();
      });
    });
  });

  describe('register', () => {
    it('should update state after successful registration', async () => {
      const user = userEvent.setup();

      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('loading').textContent).toBe('false');
      });

      await user.click(screen.getByText('Register'));

      await waitFor(() => {
        expect(screen.getByTestId('authenticated').textContent).toBe('true');
      });

    });

    it('should not write a token to localStorage after registration', async () => {
      const user = userEvent.setup();

      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('loading').textContent).toBe('false');
      });

      await user.click(screen.getByText('Register'));

      await waitFor(() => {
        expect(screen.getByTestId('authenticated').textContent).toBe('true');
      });
      await waitFor(() => {
        expect(localStorage.getItem('movie_ranking_token')).toBeNull();
        expect(localStorage.length).toBe(0);
      });
    });

    it('should throw error on duplicate email registration', async () => {
      const user = userEvent.setup();
      const onError = vi.fn();

      function ErrorTestComponent() {
        const { register } = useAuth();

        const handleRegister = async () => {
          try {
            // MOCK_USER_EMAIL is already registered
            await register(MOCK_USER_EMAIL, 'password123');
          } catch (e) {
            onError(e);
          }
        };

        return <button onClick={handleRegister}>Register Duplicate</button>;
      }

      render(
        <AuthProvider>
          <ErrorTestComponent />
        </AuthProvider>
      );

      await user.click(screen.getByText('Register Duplicate'));

      await waitFor(() => {
        expect(onError).toHaveBeenCalled();
      });
    });
  });

  describe('logout', () => {
    it('should clear authentication state on logout', async () => {
      const user = userEvent.setup();

      // Start with an authenticated cookie session
      setMockSession(true);

      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('authenticated').textContent).toBe('true');
      });

      // Click logout
      await user.click(screen.getByText('Logout'));

      await waitFor(() => {
        expect(screen.getByTestId('authenticated').textContent).toBe('false');
      });
    });

    it('should call POST /auth/logout/ so the server clears the session', async () => {
      const user = userEvent.setup();
      setMockSession(true);

      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('authenticated').textContent).toBe('true');
      });

      await user.click(screen.getByText('Logout'));

      await waitFor(() => {
        expect(screen.getByTestId('authenticated').textContent).toBe('false');
      });
      expect(hasMockSession()).toBe(false);
    });
  });

  describe('unauthorized (401) handling', () => {
    it('should clear state and ask the server to expire the cookies on a 401', async () => {
      const logoutCalled = vi.fn();
      server.use(
        http.post('/api/v1/auth/logout/', () => {
          logoutCalled();
          return new HttpResponse(null, { status: 204 });
        })
      );
      setMockSession(true);

      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('authenticated').textContent).toBe('true');
      });

      // The session expires server-side; the next API call returns 401
      setMockSession(false);
      await apiClient.getRankings().catch(() => undefined);

      await waitFor(() => {
        expect(screen.getByTestId('authenticated').textContent).toBe('false');
      });
      await waitFor(() => expect(logoutCalled).toHaveBeenCalledTimes(1));
      expect(localStorage.length).toBe(0);
    });
  });

  describe('useAuth hook', () => {
    it('should throw error when used outside AuthProvider', () => {
      // Suppress console.error for this test
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      function TestComponent() {
        useAuth();
        return null;
      }

      expect(() => render(<TestComponent />)).toThrow(
        'useAuth must be used within an AuthProvider'
      );

      consoleSpy.mockRestore();
    });
  });
});
