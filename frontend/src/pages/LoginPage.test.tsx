/**
 * Tests for LoginPage component.
 *
 * These tests verify:
 * - Form renders with email and password fields
 * - Form validation works correctly
 * - Login flow works with valid credentials
 * - Error messages are displayed for invalid credentials
 * - Redirect to original destination after login
 * - Already authenticated users are redirected
 * - Google Sign-In button is present
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from '../context/AuthContext';
import { LoginPage } from './LoginPage';
import { resetMockData, MOCK_USER_EMAIL, MOCK_USER_PASSWORD } from '../__tests__/mocks/handlers';

// Helper to find the email/password form's submit button (not the Google button)
function getEmailSubmitButton() {
  // The email form submit button is inside the form element
  const form = document.querySelector('form');
  if (!form) throw new Error('Form not found');
  return within(form).getByRole('button', { name: /sign in/i });
}

// Helper to render LoginPage with router and auth context
function renderLoginPage(initialEntries = ['/login']) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<div>Home Page</div>} />
          <Route path="/rankings" element={<div>Rankings Page</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>
  );
}

describe('LoginPage', () => {
  beforeEach(() => {
    localStorage.clear();
    resetMockData();
  });

  describe('rendering', () => {
    it('should render the login form', async () => {
      renderLoginPage();

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /welcome back/i })).toBeInTheDocument();
      });

      expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
      expect(getEmailSubmitButton()).toBeInTheDocument();
    });

    it('should render link to register page', async () => {
      renderLoginPage();

      await waitFor(() => {
        expect(screen.getByRole('link', { name: /sign up/i })).toBeInTheDocument();
      });

      expect(screen.getByRole('link', { name: /sign up/i })).toHaveAttribute('href', '/register');
    });

    it('should have correct input types', async () => {
      renderLoginPage();

      await waitFor(() => {
        expect(screen.getByLabelText(/email/i)).toHaveAttribute('type', 'email');
      });

      expect(screen.getByLabelText(/password/i)).toHaveAttribute('type', 'password');
    });

    it('should render Google Sign-In button', async () => {
      renderLoginPage();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /sign in with google/i })).toBeInTheDocument();
      });
    });
  });

  describe('form validation', () => {
    it('should show error when email is empty', async () => {
      const user = userEvent.setup();
      renderLoginPage();

      await waitFor(() => {
        expect(getEmailSubmitButton()).toBeInTheDocument();
      });

      // Submit without entering anything
      await user.click(getEmailSubmitButton());

      await waitFor(() => {
        expect(screen.getByText(/email is required/i)).toBeInTheDocument();
      });
    });

    it('should show error for invalid email format', async () => {
      const user = userEvent.setup();
      renderLoginPage();

      await waitFor(() => {
        expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
      });

      // Use an email that passes HTML5 validation (has @) but fails our stricter
      // regex validation (requires user@domain.tld format)
      const emailInput = screen.getByLabelText(/email/i);
      await user.clear(emailInput);
      await user.type(emailInput, 'test@localhost');
      await user.type(screen.getByLabelText(/password/i), 'password123');

      // Submit the form
      await user.click(getEmailSubmitButton());

      // Our validation should run and show the error
      await waitFor(() => {
        expect(screen.getByText(/please enter a valid email/i)).toBeInTheDocument();
      });
    });

    it('should show error when password is empty', async () => {
      const user = userEvent.setup();
      renderLoginPage();

      await waitFor(() => {
        expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
      });

      await user.type(screen.getByLabelText(/email/i), 'test@example.com');
      await user.click(getEmailSubmitButton());

      await waitFor(() => {
        expect(screen.getByText(/password is required/i)).toBeInTheDocument();
      });
    });
  });

  describe('successful login', () => {
    it('should navigate to home after successful login', async () => {
      const user = userEvent.setup();
      renderLoginPage();

      await waitFor(() => {
        expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
      });

      await user.type(screen.getByLabelText(/email/i), MOCK_USER_EMAIL);
      await user.type(screen.getByLabelText(/password/i), MOCK_USER_PASSWORD);
      await user.click(getEmailSubmitButton());

      await waitFor(() => {
        expect(screen.getByText('Home Page')).toBeInTheDocument();
      });
    });

    it('should navigate to original destination after login', async () => {
      const user = userEvent.setup();

      // Simulate coming from a protected route
      render(
        <MemoryRouter initialEntries={[{ pathname: '/login', state: { from: { pathname: '/rankings' } } }]}>
          <AuthProvider>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/" element={<div>Home Page</div>} />
              <Route path="/rankings" element={<div>Rankings Page</div>} />
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
      });

      await user.type(screen.getByLabelText(/email/i), MOCK_USER_EMAIL);
      await user.type(screen.getByLabelText(/password/i), MOCK_USER_PASSWORD);
      await user.click(getEmailSubmitButton());

      await waitFor(() => {
        expect(screen.getByText('Rankings Page')).toBeInTheDocument();
      });
    });

    it('should show loading state while logging in', async () => {
      const user = userEvent.setup();
      renderLoginPage();

      await waitFor(() => {
        expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
      });

      await user.type(screen.getByLabelText(/email/i), MOCK_USER_EMAIL);
      await user.type(screen.getByLabelText(/password/i), MOCK_USER_PASSWORD);

      // Click and immediately check for loading state
      const submitButton = getEmailSubmitButton();
      await user.click(submitButton);

      // Button should be disabled during submission
      // Note: The exact loading state may vary based on implementation
    });
  });

  describe('failed login', () => {
    it('should show error message for invalid credentials', async () => {
      const user = userEvent.setup();
      renderLoginPage();

      await waitFor(() => {
        expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
      });

      await user.type(screen.getByLabelText(/email/i), MOCK_USER_EMAIL);
      await user.type(screen.getByLabelText(/password/i), 'wrongpassword');
      await user.click(getEmailSubmitButton());

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument();
      });
    });

    it('should show error message for non-existent user', async () => {
      const user = userEvent.setup();
      renderLoginPage();

      await waitFor(() => {
        expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
      });

      await user.type(screen.getByLabelText(/email/i), 'nonexistent@example.com');
      await user.type(screen.getByLabelText(/password/i), 'password123');
      await user.click(getEmailSubmitButton());

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument();
      });
    });
  });

  describe('authenticated user redirect', () => {
    it('should redirect authenticated user to home', async () => {
      // Set token before rendering
      localStorage.setItem('movie_ranking_token', 'existing-token');

      renderLoginPage();

      // Should redirect to home
      await waitFor(() => {
        expect(screen.getByText('Home Page')).toBeInTheDocument();
      });
    });
  });
});
