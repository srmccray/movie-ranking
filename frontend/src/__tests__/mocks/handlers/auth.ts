/** Auth handlers: register, login, Google OAuth login/callback/link and current user. */

import { http, HttpResponse } from 'msw';
import {
  MOCK_TOKEN,
  MOCK_USER_EMAIL,
  registeredUsers,
  validOAuthStates,
  validLinkStates,
  userHasGoogleLinked,
} from './state';

export const authHandlers = [
  // POST /api/v1/auth/register
  http.post('/api/v1/auth/register', async ({ request }) => {
    const contentType = request.headers.get('Content-Type');

    // Registration should use JSON
    if (!contentType?.includes('application/json')) {
      return HttpResponse.json(
        { detail: 'Content-Type must be application/json' },
        { status: 415 }
      );
    }

    const body = (await request.json()) as { email?: string; password?: string };

    if (!body.email || !body.password) {
      return HttpResponse.json(
        { detail: 'Email and password are required' },
        { status: 422 }
      );
    }

    // Check if email is already registered
    if (registeredUsers.has(body.email)) {
      return HttpResponse.json(
        { detail: 'Email already registered' },
        { status: 409 }
      );
    }

    // Register the user
    registeredUsers.set(body.email, body.password);

    return HttpResponse.json(
      {
        access_token: MOCK_TOKEN,
        token_type: 'bearer',
      },
      { status: 201 }
    );
  }),

  // POST /api/v1/auth/login
  http.post('/api/v1/auth/login', async ({ request }) => {
    const contentType = request.headers.get('Content-Type');

    // Login MUST use form-urlencoded (this was the bug!)
    if (!contentType?.includes('application/x-www-form-urlencoded')) {
      return HttpResponse.json(
        {
          detail: [
            {
              loc: ['body'],
              msg: 'Expected form-urlencoded data',
              type: 'value_error',
            },
          ],
        },
        { status: 422 }
      );
    }

    const formData = await request.text();
    const params = new URLSearchParams(formData);
    const username = params.get('username');
    const password = params.get('password');

    if (!username || !password) {
      return HttpResponse.json(
        { detail: 'Username and password are required' },
        { status: 422 }
      );
    }

    // Check credentials
    const storedPassword = registeredUsers.get(username);
    if (!storedPassword || storedPassword !== password) {
      return HttpResponse.json(
        { detail: 'Invalid email or password' },
        { status: 401 }
      );
    }

    return HttpResponse.json({
      access_token: MOCK_TOKEN,
      token_type: 'bearer',
    });
  }),

  // GET /api/v1/auth/google/login/
  http.get('/api/v1/auth/google/login/', () => {
    // Generate a new state and store it
    const newState = `state-${Date.now()}`;
    validOAuthStates.add(newState);

    return HttpResponse.json({
      authorization_url: `https://accounts.google.com/o/oauth2/v2/auth?client_id=test&redirect_uri=http://localhost:8000/api/v1/auth/google/callback/&response_type=code&scope=openid%20email%20profile&state=${newState}`,
    });
  }),

  // GET /api/v1/auth/google/callback/
  http.get('/api/v1/auth/google/callback/', ({ request }) => {
    const url = new URL(request.url);
    const code = url.searchParams.get('code');
    const state = url.searchParams.get('state');
    const error = url.searchParams.get('error');

    // Handle user cancellation
    if (error) {
      return HttpResponse.json(
        { detail: 'Authentication cancelled' },
        { status: 400 }
      );
    }

    // Check for missing parameters
    if (!code || !state) {
      return HttpResponse.json(
        { detail: 'Missing required parameters' },
        { status: 400 }
      );
    }

    // Validate state (CSRF protection)
    if (!validOAuthStates.has(state)) {
      return HttpResponse.json(
        { detail: 'Invalid or expired authentication state' },
        { status: 400 }
      );
    }

    // Remove used state
    validOAuthStates.delete(state);

    // Return mock token
    return HttpResponse.json({
      access_token: MOCK_TOKEN,
      token_type: 'bearer',
    });
  }),

  // GET /api/v1/auth/me/
  http.get('/api/v1/auth/me/', ({ request }) => {
    const authHeader = request.headers.get('Authorization');

    if (!authHeader?.startsWith('Bearer ')) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }

    return HttpResponse.json({
      id: 'user-123',
      email: MOCK_USER_EMAIL,
      auth_provider: userHasGoogleLinked ? 'linked' : 'local',
      has_google_linked: userHasGoogleLinked,
      has_password: true,
      created_at: '2024-01-01T00:00:00Z',
    });
  }),

  // GET /api/v1/auth/google/link/
  http.get('/api/v1/auth/google/link/', ({ request }) => {
    const authHeader = request.headers.get('Authorization');

    if (!authHeader?.startsWith('Bearer ')) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }

    // Check if already linked
    if (userHasGoogleLinked) {
      return HttpResponse.json(
        { detail: 'Google account already linked' },
        { status: 409 }
      );
    }

    // Generate a link state
    const linkState = `link-state-${Date.now()}`;
    validLinkStates.add(linkState);

    return HttpResponse.json({
      authorization_url: `https://accounts.google.com/o/oauth2/v2/auth?client_id=test&redirect_uri=http://localhost:3000/settings&response_type=code&scope=openid%20email%20profile&state=${linkState}`,
    });
  }),
];
