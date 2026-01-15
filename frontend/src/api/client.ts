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
} from '../types';

const API_BASE = '/api/v1';

class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: HeadersInit = {
      ...options.headers,
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

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
    });

    if (!response.ok) {
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

  // Google OAuth endpoints
  async getGoogleAuthUrl(): Promise<GoogleAuthUrlResponse> {
    // Pass the frontend callback URL so backend redirects there with the token
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
