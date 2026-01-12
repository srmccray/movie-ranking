/**
 * Tests for the API client.
 *
 * These tests verify:
 * - Login method sends correct Content-Type (application/x-www-form-urlencoded)
 * - Register method works with JSON Content-Type
 * - Token is properly included in authenticated requests
 * - Error handling works correctly
 *
 * The Content-Type bug fix is specifically tested here:
 * The login endpoint requires form-urlencoded data, and the old code was
 * overwriting the Content-Type to application/json, causing login to fail.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { apiClient, ApiClientError } from './client';
import { resetMockData, MOCK_TOKEN, MOCK_USER_EMAIL, MOCK_USER_PASSWORD } from '../__tests__/mocks/handlers';

describe('ApiClient', () => {
  beforeEach(() => {
    // Reset the API client token before each test
    apiClient.setToken(null);
    // Reset mock data
    resetMockData();
  });

  describe('login', () => {
    it('should successfully login with valid credentials', async () => {
      const result = await apiClient.login(MOCK_USER_EMAIL, MOCK_USER_PASSWORD);

      expect(result).toBeDefined();
      expect(result.access_token).toBe(MOCK_TOKEN);
    });

    it('should send form-urlencoded Content-Type for login', async () => {
      // This test specifically verifies the Content-Type bug fix
      // The login endpoint requires application/x-www-form-urlencoded
      const fetchSpy = vi.spyOn(global, 'fetch');

      await apiClient.login(MOCK_USER_EMAIL, MOCK_USER_PASSWORD);

      expect(fetchSpy).toHaveBeenCalled();
      const [, options] = fetchSpy.mock.calls[0];
      const headers = options?.headers as Record<string, string>;

      // Verify Content-Type is form-urlencoded, NOT application/json
      expect(headers['Content-Type']).toBe('application/x-www-form-urlencoded');

      fetchSpy.mockRestore();
    });

    it('should send username and password as form data', async () => {
      const fetchSpy = vi.spyOn(global, 'fetch');

      await apiClient.login(MOCK_USER_EMAIL, MOCK_USER_PASSWORD);

      const [, options] = fetchSpy.mock.calls[0];
      const body = options?.body as string;

      // Body should be URL-encoded form data
      expect(body).toContain('username=');
      expect(body).toContain('password=');
      expect(body).toContain(encodeURIComponent(MOCK_USER_EMAIL));
      expect(body).toContain(encodeURIComponent(MOCK_USER_PASSWORD));

      fetchSpy.mockRestore();
    });

    it('should throw ApiClientError on invalid credentials', async () => {
      await expect(
        apiClient.login(MOCK_USER_EMAIL, 'wrongpassword')
      ).rejects.toThrow(ApiClientError);

      try {
        await apiClient.login(MOCK_USER_EMAIL, 'wrongpassword');
      } catch (error) {
        expect(error).toBeInstanceOf(ApiClientError);
        expect((error as ApiClientError).status).toBe(401);
      }
    });

    it('should throw ApiClientError on non-existent user', async () => {
      await expect(
        apiClient.login('nonexistent@example.com', 'password')
      ).rejects.toThrow(ApiClientError);
    });
  });

  describe('register', () => {
    it('should successfully register a new user', async () => {
      const result = await apiClient.register('newuser@example.com', 'newpassword123');

      expect(result).toBeDefined();
      expect(result.access_token).toBe(MOCK_TOKEN);
    });

    it('should send JSON Content-Type for register', async () => {
      const fetchSpy = vi.spyOn(global, 'fetch');

      await apiClient.register('another@example.com', 'password123');

      expect(fetchSpy).toHaveBeenCalled();
      const [, options] = fetchSpy.mock.calls[0];
      const headers = options?.headers as Record<string, string>;

      // Register should use application/json
      expect(headers['Content-Type']).toBe('application/json');

      fetchSpy.mockRestore();
    });

    it('should send email and password in JSON body', async () => {
      const fetchSpy = vi.spyOn(global, 'fetch');

      await apiClient.register('json@example.com', 'password123');

      const [, options] = fetchSpy.mock.calls[0];
      const body = JSON.parse(options?.body as string);

      expect(body.email).toBe('json@example.com');
      expect(body.password).toBe('password123');

      fetchSpy.mockRestore();
    });

    it('should throw ApiClientError on duplicate email', async () => {
      // MOCK_USER_EMAIL is already registered in mock handlers
      await expect(
        apiClient.register(MOCK_USER_EMAIL, 'password123')
      ).rejects.toThrow(ApiClientError);

      try {
        await apiClient.register(MOCK_USER_EMAIL, 'password123');
      } catch (error) {
        expect(error).toBeInstanceOf(ApiClientError);
        expect((error as ApiClientError).status).toBe(409);
      }
    });
  });

  describe('setToken', () => {
    it('should set the token for authenticated requests', async () => {
      apiClient.setToken(MOCK_TOKEN);
      const fetchSpy = vi.spyOn(global, 'fetch');

      await apiClient.getRankings();

      const [, options] = fetchSpy.mock.calls[0];
      const headers = options?.headers as Record<string, string>;

      expect(headers['Authorization']).toBe(`Bearer ${MOCK_TOKEN}`);

      fetchSpy.mockRestore();
    });

    it('should not include Authorization header when token is null', async () => {
      apiClient.setToken(null);
      const fetchSpy = vi.spyOn(global, 'fetch');

      // This will fail because no token, but we're checking the request
      try {
        await apiClient.getRankings();
      } catch {
        // Expected to fail
      }

      const [, options] = fetchSpy.mock.calls[0];
      const headers = options?.headers as Record<string, string>;

      expect(headers['Authorization']).toBeUndefined();

      fetchSpy.mockRestore();
    });
  });

  describe('createMovie', () => {
    beforeEach(() => {
      apiClient.setToken(MOCK_TOKEN);
    });

    it('should create a movie with authentication', async () => {
      const result = await apiClient.createMovie({ title: 'Test Movie', year: 2024 });

      expect(result).toBeDefined();
      expect(result.title).toBe('Test Movie');
      expect(result.year).toBe(2024);
    });

    it('should send JSON Content-Type for movie creation', async () => {
      const fetchSpy = vi.spyOn(global, 'fetch');

      await apiClient.createMovie({ title: 'Another Movie' });

      const [, options] = fetchSpy.mock.calls[0];
      const headers = options?.headers as Record<string, string>;

      expect(headers['Content-Type']).toBe('application/json');

      fetchSpy.mockRestore();
    });

    it('should include trailing slash in URL', async () => {
      const fetchSpy = vi.spyOn(global, 'fetch');

      await apiClient.createMovie({ title: 'Slash Movie' });

      const [url] = fetchSpy.mock.calls[0];
      expect(url).toContain('/movies/');

      fetchSpy.mockRestore();
    });

    it('should throw ApiClientError when not authenticated', async () => {
      apiClient.setToken(null);

      await expect(
        apiClient.createMovie({ title: 'Test Movie' })
      ).rejects.toThrow(ApiClientError);
    });
  });

  describe('createOrUpdateRanking', () => {
    beforeEach(async () => {
      apiClient.setToken(MOCK_TOKEN);
    });

    it('should include trailing slash in URL', async () => {
      const fetchSpy = vi.spyOn(global, 'fetch');

      // Create a movie first to have a valid movie_id
      const movie = await apiClient.createMovie({ title: 'Rating Test Movie' });

      await apiClient.createOrUpdateRanking({ movie_id: movie.id, rating: 5 });

      // Find the ranking request (second call)
      const rankingCall = fetchSpy.mock.calls.find(call =>
        (call[0] as string).includes('/rankings/')
      );

      expect(rankingCall).toBeDefined();
      expect(rankingCall?.[0]).toContain('/rankings/');

      fetchSpy.mockRestore();
    });
  });

  describe('getRankings', () => {
    beforeEach(() => {
      apiClient.setToken(MOCK_TOKEN);
    });

    it('should fetch rankings with authentication', async () => {
      const result = await apiClient.getRankings();

      expect(result).toBeDefined();
      expect(result.items).toBeDefined();
      expect(Array.isArray(result.items)).toBe(true);
    });

    it('should include trailing slash in URL', async () => {
      const fetchSpy = vi.spyOn(global, 'fetch');

      await apiClient.getRankings();

      const [url] = fetchSpy.mock.calls[0];
      expect(url).toContain('/rankings/');

      fetchSpy.mockRestore();
    });

    it('should pass limit and offset parameters', async () => {
      const fetchSpy = vi.spyOn(global, 'fetch');

      await apiClient.getRankings(10, 5);

      const [url] = fetchSpy.mock.calls[0];
      expect(url).toContain('limit=10');
      expect(url).toContain('offset=5');

      fetchSpy.mockRestore();
    });
  });
});

describe('ApiClientError', () => {
  it('should create error with string detail message', () => {
    const error = new ApiClientError(401, { detail: 'Invalid credentials' });

    expect(error.message).toBe('Invalid credentials');
    expect(error.status).toBe(401);
  });

  it('should create error with validation error array', () => {
    const error = new ApiClientError(422, {
      detail: [
        { loc: ['body', 'email'], msg: 'Invalid email', type: 'value_error' },
      ],
    });

    expect(error.message).toBe('Invalid email');
    expect(error.status).toBe(422);
  });

  it('should use empty string when detail is empty string', () => {
    // Note: Empty string is truthy for typeof check, so it's used as-is
    const error = new ApiClientError(500, { detail: '' });

    expect(error.message).toBe('');
  });

  it('should use default message when detail is undefined', () => {
    // When detail is not provided or undefined, default message is used
    const error = new ApiClientError(500, {} as { detail: string });

    expect(error.message).toBe('An error occurred');
  });
});
