import type {
  Token,
  Movie,
  Ranking,
  RankingListResponse,
  MovieCreate,
  RankingCreate,
  ApiError,
  TMDBSearchResult,
  SortField,
  SortOrder,
  ActivityResponse,
  GenreResponse,
  StatsResponse,
  RatingDistributionResponse,
  GoogleAuthUrlResponse,
  UserProfileResponse,
  ImportSessionResponse,
  ImportSessionDetailResponse,
  ImportMovieAddRequest,
  ImportMovieMatchRequest,
  MatchedMovieItem,
} from '../types';

const API_BASE = '/api/v1';

const CSRF_COOKIE = 'csrf_token';
const CSRF_HEADER = 'X-CSRF-Token';
const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS']);

/**
 * Read the double-submit CSRF token from the (JS-readable) `csrf_token` cookie.
 * The httpOnly `session` cookie is never visible here by design (ADR-0013).
 */
export function getCsrfToken(): string | null {
  for (const part of document.cookie.split(';')) {
    const [name, ...rest] = part.trim().split('=');
    if (name === CSRF_COOKIE) {
      return decodeURIComponent(rest.join('='));
    }
  }
  return null;
}

/** Add the CSRF header for unsafe methods when the cookie is present. */
function withCsrfHeader(
  headers: Record<string, string>,
  method: string | undefined
): Record<string, string> {
  if (SAFE_METHODS.has((method ?? 'GET').toUpperCase())) {
    return headers;
  }
  const csrf = getCsrfToken();
  return csrf ? { ...headers, [CSRF_HEADER]: csrf } : headers;
}

class ApiClient {
  private onUnauthorized: (() => void) | null = null;

  setOnUnauthorized(callback: (() => void) | null) {
    this.onUnauthorized = callback;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = withCsrfHeader(
      { ...(options.headers as Record<string, string> | undefined) },
      options.method
    );

    // Only set JSON content-type if not already specified and body is not FormData
    if (
      options.body &&
      !(options.body instanceof FormData) &&
      !headers['Content-Type']
    ) {
      headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
      credentials: 'include',
    });

    if (!response.ok) {
      // Handle 401 Unauthorized - trigger logout callback
      if (response.status === 401 && endpoint !== '/auth/logout/' && this.onUnauthorized) {
        this.onUnauthorized();
      }

      const error: ApiError = await response.json();
      throw new ApiClientError(response.status, error);
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return undefined as T;
    }

    return response.json();
  }

  // Auth endpoints
  async register(email: string, password: string): Promise<Token> {
    return this.request<Token>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  }

  async login(email: string, password: string): Promise<Token> {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    return this.request<Token>('/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData.toString(),
    });
  }

  /** Clear the session and CSRF cookies on the server. */
  async logout(): Promise<void> {
    return this.request<void>('/auth/logout/', { method: 'POST' });
  }

  // Google OAuth endpoints
  async getGoogleAuthUrl(): Promise<GoogleAuthUrlResponse> {
    // Pass the frontend callback URL so backend redirects there after setting the session cookie
    const redirectUri = `${window.location.origin}/auth/google/callback`;
    const params = new URLSearchParams({ redirect_uri: redirectUri });
    return this.request<GoogleAuthUrlResponse>(`/auth/google/login/?${params.toString()}`);
  }

  async getGoogleLinkUrl(): Promise<GoogleAuthUrlResponse> {
    // Pass the frontend settings page URL so backend redirects there after linking
    const redirectUri = `${window.location.origin}/settings`;
    const params = new URLSearchParams({ redirect_uri: redirectUri });
    return this.request<GoogleAuthUrlResponse>(`/auth/google/link/?${params.toString()}`);
  }

  // User profile endpoints
  async getCurrentUser(): Promise<UserProfileResponse> {
    return this.request<UserProfileResponse>('/auth/me/');
  }

  // Movie endpoints
  async createMovie(data: MovieCreate): Promise<Movie> {
    return this.request<Movie>('/movies/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async searchMovies(query: string, year?: number): Promise<TMDBSearchResult[]> {
    const params = new URLSearchParams({ q: query });
    if (year !== undefined) {
      params.append('year', year.toString());
    }
    const response = await this.request<{ results: TMDBSearchResult[]; query: string; year: number | null }>(
      `/movies/search/?${params.toString()}`
    );
    return response.results;
  }

  // Ranking endpoints
  async createOrUpdateRanking(data: RankingCreate): Promise<Ranking> {
    return this.request<Ranking>('/rankings/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getRankings(
    limit = 20,
    offset = 0,
    sortBy: SortField = 'rated_at',
    sortOrder: SortOrder = 'desc'
  ): Promise<RankingListResponse> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
      sort_by: sortBy,
      sort_order: sortOrder,
    });
    return this.request<RankingListResponse>(`/rankings/?${params.toString()}`);
  }

  async deleteRanking(rankingId: string): Promise<void> {
    await this.request<void>(`/rankings/${rankingId}/`, {
      method: 'DELETE',
    });
  }

  async clearAllRankings(): Promise<void> {
    await this.request<void>('/rankings/all/', {
      method: 'DELETE',
    });
  }

  // Analytics endpoints
  async getActivity(): Promise<ActivityResponse> {
    return this.request<ActivityResponse>('/analytics/activity/');
  }

  async getGenres(): Promise<GenreResponse> {
    return this.request<GenreResponse>('/analytics/genres/');
  }

  async getStats(): Promise<StatsResponse> {
    return this.request<StatsResponse>('/analytics/stats/');
  }

  async getRatingDistribution(): Promise<RatingDistributionResponse> {
    return this.request<RatingDistributionResponse>('/analytics/rating-distribution/');
  }

  // ============================================
  // Amazon Prime Import Methods
  // ============================================

  /**
   * Upload an Amazon Prime CSV file to start an import session.
   * @param file - The CSV file to upload
   * @returns Import session with matched movies
   */
  async uploadAmazonPrimeCSV(file: File): Promise<ImportSessionResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const headers = withCsrfHeader({}, 'POST');
    // Note: Don't set Content-Type for FormData - browser sets it with boundary

    const response = await fetch(`${API_BASE}/import/amazon-prime/upload/`, {
      method: 'POST',
      headers,
      body: formData,
      credentials: 'include',
    });

    if (!response.ok) {
      // Handle 401 Unauthorized - trigger logout callback
      if (response.status === 401 && this.onUnauthorized) {
        this.onUnauthorized();
      }

      const error: ApiError = await response.json();
      throw new ApiClientError(response.status, error);
    }

    return response.json();
  }

  /**
   * Get the current state of an import session.
   * @param sessionId - The session ID from upload response
   * @returns Current session state with progress
   */
  async getImportSession(sessionId: string): Promise<ImportSessionDetailResponse> {
    return this.request<ImportSessionDetailResponse>(
      `/import/amazon-prime/session/${sessionId}/`
    );
  }

  /**
   * Add a movie from the import session to user's rankings.
   * @param sessionId - The session ID
   * @param movieIndex - Index of the movie in the session
   * @param rating - Rating to assign (1-5)
   * @param ratedAt - Optional rated_at timestamp (ISO 8601)
   * @returns The created ranking
   */
  async addImportMovie(
    sessionId: string,
    movieIndex: number,
    rating: number,
    ratedAt?: string
  ): Promise<Ranking> {
    const body: ImportMovieAddRequest = { rating };
    if (ratedAt) {
      body.rated_at = ratedAt;
    }

    return this.request<Ranking>(
      `/import/amazon-prime/session/${sessionId}/movie/${movieIndex}/add/`,
      {
        method: 'POST',
        body: JSON.stringify(body),
      }
    );
  }

  /**
   * Skip a movie in the import session.
   * @param sessionId - The session ID
   * @param movieIndex - Index of the movie to skip
   */
  async skipImportMovie(sessionId: string, movieIndex: number): Promise<void> {
    await this.request<void>(
      `/import/amazon-prime/session/${sessionId}/movie/${movieIndex}/skip/`,
      { method: 'POST' }
    );
  }

  /**
   * Cancel and delete an import session.
   * @param sessionId - The session ID to cancel
   */
  async cancelImportSession(sessionId: string): Promise<void> {
    await this.request<void>(
      `/import/amazon-prime/session/${sessionId}/`,
      { method: 'DELETE' }
    );
  }

  /**
   * Update the TMDB match for a movie in the import session.
   * @param sessionId - The session ID
   * @param movieIndex - Index of the movie in the session
   * @param match - The new TMDB match data
   * @returns The updated MatchedMovieItem
   */
  async updateImportMovieMatch(
    sessionId: string,
    movieIndex: number,
    match: ImportMovieMatchRequest
  ): Promise<MatchedMovieItem> {
    return this.request<MatchedMovieItem>(
      `/import/amazon-prime/session/${sessionId}/movie/${movieIndex}/match/`,
      {
        method: 'PATCH',
        body: JSON.stringify(match),
      }
    );
  }
}

export class ApiClientError extends Error {
  constructor(
    public status: number,
    public error: ApiError
  ) {
    const message =
      typeof error.detail === 'string'
        ? error.detail
        : error.detail?.[0]?.msg || 'An error occurred';
    super(message);
    this.name = 'ApiClientError';
  }
}

export const apiClient = new ApiClient();
