import type {
  Token,
  Movie,
  Ranking,
  RankingListResponse,
  MovieCreate,
  RankingCreate,
  ApiError,
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

  // Movie endpoints
  async createMovie(data: MovieCreate): Promise<Movie> {
    return this.request<Movie>('/movies/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Ranking endpoints
  async createOrUpdateRanking(data: RankingCreate): Promise<Ranking> {
    return this.request<Ranking>('/rankings/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getRankings(limit = 20, offset = 0): Promise<RankingListResponse> {
    return this.request<RankingListResponse>(
      `/rankings/?limit=${limit}&offset=${offset}`
    );
  }

  async deleteRanking(rankingId: string): Promise<void> {
    await this.request<void>(`/rankings/${rankingId}/`, {
      method: 'DELETE',
    });
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
