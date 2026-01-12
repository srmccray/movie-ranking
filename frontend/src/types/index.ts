// API Response Types

export interface Token {
  access_token: string;
  token_type: string;
}

export interface Movie {
  id: string;
  title: string;
  year: number | null;
  created_at: string;
}

export interface MovieBrief {
  id: string;
  title: string;
  year: number | null;
}

export interface Ranking {
  id: string;
  movie_id: string;
  rating: number;
  rated_at: string;
  created_at: string;
  updated_at: string;
}

export interface RankingWithMovie {
  id: string;
  rating: number;
  rated_at: string;
  created_at: string;
  updated_at: string;
  movie: MovieBrief;
}

export interface RankingListResponse {
  items: RankingWithMovie[];
  total: number;
  limit: number;
  offset: number;
}

// Request Types

export interface UserCreate {
  email: string;
  password: string;
}

export interface MovieCreate {
  title: string;
  year?: number | null;
}

export interface RankingCreate {
  movie_id: string;
  rating: number;
  rated_at?: string;
}

// API Error Types

export interface ApiError {
  detail: string | ValidationError[];
}

export interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

// Auth Context Types

export interface AuthState {
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}
