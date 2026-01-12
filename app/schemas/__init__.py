"""Pydantic schemas for request/response validation."""

from app.schemas.movie import (
    GenreResponse,
    MovieBrief,
    MovieCreate,
    MovieResponse,
    TMDBMovieDetails,
    TMDBSearchResponse,
    TMDBSearchResult,
)
from app.schemas.ranking import (
    RankingCreate,
    RankingListResponse,
    RankingResponse,
    RankingWithMovie,
)
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserResponse

__all__ = [
    "GenreResponse",
    "MovieBrief",
    "MovieCreate",
    "MovieResponse",
    "RankingCreate",
    "RankingListResponse",
    "RankingResponse",
    "RankingWithMovie",
    "TMDBMovieDetails",
    "TMDBSearchResponse",
    "TMDBSearchResult",
    "Token",
    "UserCreate",
    "UserResponse",
]
