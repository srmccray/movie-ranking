/**
 * Tests for GoogleCallbackPage component.
 *
 * These tests verify:
 * - Loading state shows while processing callback
 * - Success state redirects to home when token is received
 * - Error states display appropriate messages
 * - OAuth error handling (user cancelled, missing token, etc.)
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from '../context/AuthContext';
import { GoogleCallbackPage } from './GoogleCallbackPage';
import { resetMockData } from '../__tests__/mocks/handlers';

// Helper to render GoogleCallbackPage with router and auth context
function renderCallbackPage(searchParams = '') {
  const path = `/auth/google/callback${searchParams ? `?${searchParams}` : ''}`;

  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <Routes>
          <Route path="/auth/google/callback" element={<GoogleCallbackPage />} />
          <Route path="/" element={<div>Home Page</div>} />
          <Route path="/login" element={<div>Login Page</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>
  );
}

describe('GoogleCallbackPage', () => {
  beforeEach(() => {
    localStorage.clear();
    resetMockData();
  });

  describe('successful callback', () => {
    it('should redirect to home after receiving valid token', async () => {
      renderCallbackPage('token=valid-jwt-token');

      // Should eventually navigate to home
      await waitFor(
        () => {
          expect(screen.getByText('Home Page')).toBeInTheDocument();
        },
        { timeout: 2000 }
      );
    });

    it('should store token in localStorage after success', async () => {
      renderCallbackPage('token=valid-jwt-token');

      await waitFor(
        () => {
          const token = localStorage.getItem('movie_ranking_token');
          expect(token).toBe('valid-jwt-token');
        },
        { timeout: 2000 }
      );
    });

    it('should show success state or redirect to home', async () => {
      renderCallbackPage('token=valid-jwt-token');

      // Either success message appears or we've already redirected to home
      // The redirect is fast (500ms delay) so we may not catch the success state
      await waitFor(() => {
        const hasSuccess = screen.queryByText(/success/i);
        const hasHome = screen.queryByText('Home Page');
        expect(hasSuccess || hasHome).toBeTruthy();
      });
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

    it('should show error for missing token parameter', async () => {
      renderCallbackPage('');

      await waitFor(() => {
        expect(screen.getByText(/invalid callback/i)).toBeInTheDocument();
      });
    });

    it('should show error message about no token received', async () => {
      renderCallbackPage('');

      await waitFor(() => {
        expect(screen.getByText(/no authentication token received/i)).toBeInTheDocument();
      });
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
      // Set token before rendering (simulate already logged in)
      localStorage.setItem('movie_ranking_token', 'existing-token');

      renderCallbackPage('token=new-token');

      // Should redirect to home immediately
      await waitFor(() => {
        expect(screen.getByText('Home Page')).toBeInTheDocument();
      });
    });
  });
});
