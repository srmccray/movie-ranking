"""Pydantic schemas for request/response validation."""

from app.schemas.import_amazon import (
    ImportCompletionResponse,
    ImportMovieAddRequest,
    ImportMovieMatchRequest,
    ImportSessionDetailResponse,
    ImportSessionResponse,
    MatchedMovieItem,
    ParsedMovieItem,
    TMDBMatchResult,
)
from app.schemas.movie import (
    GenreResponse,
    MovieBrief,
    MovieCreate,
    MovieResponse,
    TMDBMovieDetails,
    TMDBSearchResponse,
    TMDBSearchResult,
)
from app.schemas.oauth import (
    AccountLinkingResponse,
    GoogleAuthUrlResponse,
    GoogleCallbackError,
)
from app.schemas.ranking import (
    RankingCreate,
    RankingListResponse,
    RankingResponse,
    RankingWithMovie,
)
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserProfileResponse, UserResponse

__all__ = [
    "AccountLinkingResponse",
    "GenreResponse",
    "GoogleAuthUrlResponse",
    "GoogleCallbackError",
    "ImportCompletionResponse",
    "ImportMovieAddRequest",
    "ImportMovieMatchRequest",
    "ImportSessionDetailResponse",
    "ImportSessionResponse",
    "MatchedMovieItem",
    "MovieBrief",
    "MovieCreate",
    "MovieResponse",
    "ParsedMovieItem",
    "RankingCreate",
    "RankingListResponse",
    "RankingResponse",
    "RankingWithMovie",
    "TMDBMatchResult",
    "TMDBMovieDetails",
    "TMDBSearchResponse",
    "TMDBSearchResult",
    "Token",
    "UserCreate",
    "UserProfileResponse",
    "UserResponse",
]
