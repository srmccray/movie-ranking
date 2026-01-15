"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes:
        DATABASE_URL: PostgreSQL async connection string.
        SECRET_KEY: Secret key for JWT token signing.
        ALGORITHM: JWT signing algorithm.
        ACCESS_TOKEN_EXPIRE_MINUTES: Token expiration time in minutes.
        DEBUG: Enable debug mode.
        TMDB_API_KEY: API key for The Movie Database (TMDB).
        TMDB_BASE_URL: Base URL for TMDB API.
        TMDB_IMAGE_BASE_URL: Base URL for TMDB image assets.
        GOOGLE_CLIENT_ID: Google OAuth 2.0 client ID.
        GOOGLE_CLIENT_SECRET: Google OAuth 2.0 client secret.
        GOOGLE_REDIRECT_URI: OAuth callback URI.
    """

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    DEBUG: bool = False

    # TMDB API settings
    TMDB_API_KEY: str
    TMDB_BASE_URL: str = "https://api.themoviedb.org/3"
    TMDB_IMAGE_BASE_URL: str = "https://image.tmdb.org/t/p/w185"

    # Google OAuth settings
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback/"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
