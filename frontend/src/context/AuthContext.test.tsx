/**
 * Tests for AuthContext and AuthProvider.
 *
 * These tests verify:
 * - Login flow updates authentication state
 * - Register flow updates authentication state
 * - Logout clears authentication state
 * - Token is persisted to localStorage
 * - Token is restored from localStorage on mount
 * - Error handling for failed authentication
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider, useAuth } from './AuthContext';
import { resetMockData, MOCK_TOKEN, MOCK_USER_EMAIL, MOCK_USER_PASSWORD } from '../__tests__/mocks/handlers';

// Test component that uses the auth context
function TestAuthConsumer() {
  const { token, isAuthenticated, isLoading, login, register, logout } = useAuth();

  return (
    <div>
      <div data-testid="loading">{isLoading.toString()}</div>
      <div data-testid="authenticated">{isAuthenticated.toString()}</div>
      <div data-testid="token">{token || 'null'}</div>
      <button onClick={() => login(MOCK_USER_EMAIL, MOCK_USER_PASSWORD)}>
        Login
      </button>
      <button onClick={() => register('new@example.com', 'password123')}>
        Register
      </button>
      <button onClick={logout}>Logout</button>
    </div>
  );
}

// Test component for error handling
function TestAuthErrorConsumer() {
  const { login } = useAuth();
  const [error, setError] = vi.fn().mockReturnValue(null);

  const handleLogin = async () => {
    try {
      await login('bad@example.com', 'wrongpassword');
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div>
      <button onClick={handleLogin}>Login with bad credentials</button>
      <div data-testid="error">{error || 'no error'}</div>
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
      expect(screen.getByTestId('token').textContent).toBe('null');
    });

    it('should restore token from localStorage on mount', async () => {
      // Set token in localStorage before mounting
      localStorage.setItem('movie_ranking_token', MOCK_TOKEN);

      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('loading').textContent).toBe('false');
      });

      expect(screen.getByTestId('authenticated').textContent).toBe('true');
      expect(screen.getByTestId('token').textContent).toBe(MOCK_TOKEN);
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

      expect(screen.getByTestId('token').textContent).toBe(MOCK_TOKEN);
    });

    it('should persist token to localStorage after login', async () => {
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
        expect(localStorage.getItem('movie_ranking_token')).toBe(MOCK_TOKEN);
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

      expect(screen.getByTestId('token').textContent).toBe(MOCK_TOKEN);
    });

    it('should persist token to localStorage after registration', async () => {
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
        expect(localStorage.getItem('movie_ranking_token')).toBe(MOCK_TOKEN);
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

      // Start with authenticated state
      localStorage.setItem('movie_ranking_token', MOCK_TOKEN);

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

      expect(screen.getByTestId('authenticated').textContent).toBe('false');
      expect(screen.getByTestId('token').textContent).toBe('null');
    });

    it('should remove token from localStorage on logout', async () => {
      const user = userEvent.setup();

      localStorage.setItem('movie_ranking_token', MOCK_TOKEN);

      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('authenticated').textContent).toBe('true');
      });

      await user.click(screen.getByText('Logout'));

      expect(localStorage.getItem('movie_ranking_token')).toBeNull();
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
