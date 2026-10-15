"""Application configuration using pydantic-settings."""

import logging
import os
from typing import Any

from pydantic import ValidationError
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

logger = logging.getLogger(__name__)

SSM_PREFIX_ENV = "SSM_PARAMETER_PREFIX"


def _ssm_client() -> Any:
    """Create the SSM client. Imports boto3 lazily; tests replace this function."""
    import boto3

    return boto3.client("ssm")


def load_ssm_parameters(prefix: str, allowed: set[str]) -> dict[str, Any]:
    """Fetch all parameters under ``prefix`` (paginated) as ``{name: value}``.

    Raises RuntimeError naming the prefix if SSM cannot be read. Values are
    never logged.
    """
    normalized = prefix if prefix.endswith("/") else prefix + "/"
    try:
        client = _ssm_client()
        params: dict[str, Any] = {}
        kwargs: dict[str, Any] = {
            "Path": normalized,
            "WithDecryption": True,
            "Recursive": False,
        }
        while True:
            response = client.get_parameters_by_path(**kwargs)
            for item in response.get("Parameters", []):
                name = item["Name"].removeprefix(normalized)
                if name in allowed:
                    params[name] = item["Value"]
            token = response.get("NextToken")
            if not token:
                return params
            kwargs["NextToken"] = token
    except Exception as exc:
        raise RuntimeError(
            f"Failed to load settings from SSM Parameter Store at prefix "
            f"'{normalized}' ({type(exc).__name__})"
        ) from exc


class SsmSettingsSource(PydanticBaseSettingsSource):
    """Settings source reading SecureString parameters under SSM_PARAMETER_PREFIX."""

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        return None, field_name, False  # unused; __call__ loads everything at once

    def __call__(self) -> dict[str, Any]:
        prefix = os.environ.get(SSM_PREFIX_ENV)
        if not prefix:
            return {}
        return load_ssm_parameters(prefix, set(self.settings_cls.model_fields))


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
        GOOGLE_LEGACY_TOKEN_IN_URL: Temporary; append ?token= to the redirect.
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
    # Temporary (removed by TASK-0047): append ?token=<jwt> to the callback redirect.
    GOOGLE_LEGACY_TOKEN_IN_URL: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Order (highest first): init, environment, .env, SSM, file secrets."""
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            SsmSettingsSource(settings_cls),
            file_secret_settings,
        )


def load_settings() -> Settings:
    """Build Settings, logging missing keys (never values) if SSM is in use."""
    try:
        return Settings()
    except ValidationError as exc:
        prefix = os.environ.get(SSM_PREFIX_ENV)
        if prefix:
            missing = [
                str(e["loc"][0]) for e in exc.errors() if e["type"] == "missing"
            ]
            logger.error(
                "Settings incomplete with SSM prefix '%s'; missing keys: %s",
                prefix,
                ", ".join(missing) or "(none missing; see validation errors)",
            )
        raise


settings = load_settings()
