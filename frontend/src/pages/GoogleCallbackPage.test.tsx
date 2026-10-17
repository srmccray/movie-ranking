/**
 * Tests for GoogleCallbackPage component.
 *
 * These tests verify:
 * - Loading state shows while processing callback
 * - Success state redirects to home once /auth/me/ confirms the cookie session
 * - No credential ever appears in the URL (ADR-0013); no token is stored
 * - Error states display appropriate messages
 * - OAuth error handling (user cancelled, unconfirmed session, etc.)
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom';
import { AuthProvider } from '../context/AuthContext';
import { GoogleCallbackPage } from './GoogleCallbackPage';
import { resetMockData, setMockSession } from '../__tests__/mocks/handlers';

// Helper to render GoogleCallbackPage with router and auth context
function renderCallbackPage(searchParams = '') {
  const path = `/auth/google/callback${searchParams ? `?${searchParams}` : ''}`;

  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <LocationProbe />
        <Routes>
          <Route path="/auth/google/callback" element={<GoogleCallbackPage />} />
          <Route path="/" element={<div>Home Page</div>} />
          <Route path="/login" element={<div>Login Page</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>
  );
}

// Exposes the current URL so tests can assert no credential is ever put in it.
function LocationProbe() {
  const location = useLocation();
  return <div data-testid="url">{`${location.pathname}${location.search}`}</div>;
}

describe('GoogleCallbackPage', () => {
  beforeEach(() => {
    localStorage.clear();
    resetMockData();
  });

  describe('successful callback', () => {
    it('should redirect to home once the cookie session is confirmed', async () => {
      // The backend set the httpOnly session cookie before redirecting here
      setMockSession(true);

      renderCallbackPage();

      await waitFor(
        () => {
          expect(screen.getByText('Home Page')).toBeInTheDocument();
        },
        { timeout: 2000 }
      );
    });

    it('should never put a token in the URL or localStorage', async () => {
      setMockSession(true);

      renderCallbackPage();

      await waitFor(() => {
        expect(screen.getByText('Home Page')).toBeInTheDocument();
      });

      expect(screen.getByTestId('url').textContent).not.toContain('token=');
      expect(localStorage.length).toBe(0);
    });
  });

  describe('error handling', () => {
    it('should show error when error parameter is present', async () => {
      renderCallbackPage('error=access_denied');

      await waitFor(() => {
        expect(screen.getByText(/authentication failed/i)).toBeInTheDocument();
      });
    });

    it('should show error description when provided', async () => {
      renderCallbackPage('error=access_denied&error_description=User%20cancelled');

      await waitFor(() => {
        expect(screen.getByText(/user cancelled/i)).toBeInTheDocument();
      });
    });

    it('should show an error when no session can be confirmed', async () => {
      renderCallbackPage('');

      await waitFor(() => {
        expect(screen.getByText(/invalid callback/i)).toBeInTheDocument();
      });
      expect(screen.getByText(/could not confirm your sign-in/i)).toBeInTheDocument();
    });

    it('should show Try Again button on error', async () => {
      renderCallbackPage('error=access_denied');

      await waitFor(() => {
        expect(screen.getByRole('link', { name: /try again/i })).toBeInTheDocument();
      });
    });

    it('should link back to login on error', async () => {
      renderCallbackPage('error=access_denied');

      await waitFor(() => {
        const loginLink = screen.getByRole('link', { name: /back to login/i });
        expect(loginLink).toHaveAttribute('href', '/login');
      });
    });
  });

  describe('already authenticated user', () => {
    it('should redirect to home if already authenticated', async () => {
      // Simulate an existing cookie session
      setMockSession(true);

      renderCallbackPage();

      // Should redirect to home immediately
      await waitFor(() => {
        expect(screen.getByText('Home Page')).toBeInTheDocument();
      });
    });
  });
});
