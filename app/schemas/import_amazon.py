"""Amazon Prime import schemas for request/response validation.

These schemas support the multi-step import workflow for importing
watch history from Amazon Prime Video CSV exports.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ParsedMovieItem(BaseModel):
    """A movie parsed from the Amazon Prime CSV file.

    Represents the raw data extracted from a single row in the CSV,
    filtered to only include movies (not TV series).

    Attributes:
        title: Movie title from the CSV.
        watch_date: Date the movie was watched (optional, may be null if unparseable).
        prime_image_url: Amazon Prime poster/thumbnail URL (optional fallback if TMDB fails).
    """

    title: str
    watch_date: datetime | None = None
    prime_image_url: str | None = None


class TMDBMatchResult(BaseModel):
    """TMDB search result for matching against parsed movies.

    Contains the essential fields from TMDB needed to display
    movie information during the import review flow.

    Attributes:
        tmdb_id: The movie's ID in TMDB.
        title: Movie title from TMDB.
        year: Release year (optional).
        poster_url: Full URL to poster thumbnail (optional).
        overview: Movie synopsis/description (optional).
        genre_ids: List of TMDB genre IDs (optional).
        vote_average: TMDB user rating 0.0-10.0 (optional).
        vote_count: Number of TMDB votes (optional).
        release_date: Full release date string YYYY-MM-DD (optional).
        original_language: ISO 639-1 language code (optional).
    """

    model_config = ConfigDict(from_attributes=True)

    tmdb_id: int
    title: str
    year: int | None = None
    poster_url: str | None = None
    overview: str | None = None
    genre_ids: list[int] | None = None
    vote_average: float | None = None
    vote_count: int | None = None
    release_date: str | None = None
    original_language: str | None = None


class MatchedMovieItem(BaseModel):
    """A parsed movie with TMDB match results.

    Combines the original parsed data with TMDB matching results,
    including confidence score and alternative matches.

    Attributes:
        parsed: Original movie data from CSV.
        tmdb_match: Best TMDB match (optional, null if no match found).
        confidence: Match confidence score from 0.0 (no match) to 1.0 (exact match).
        alternatives: Up to 2 alternative TMDB matches for user selection.
        status: Current status in the import workflow.
    """

    parsed: ParsedMovieItem
    tmdb_match: TMDBMatchResult | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    alternatives: list[TMDBMatchResult] = Field(default_factory=list)
    status: Literal["pending", "added", "skipped"] = "pending"


class ImportSessionResponse(BaseModel):
    """Response after uploading a CSV file for import.

    RESPONSE SHAPE: {
        session_id: "...",
        total_entries: N,
        movies_found: N,
        tv_shows_filtered: N,
        already_ranked: N,
        ready_for_review: N,
        movies: [...]
    }

    Provides a summary of the CSV parsing results and the list of
    matched movies ready for review.

    Attributes:
        session_id: Unique identifier for this import session.
        total_entries: Total rows parsed from the CSV.
        movies_found: Number of entries identified as movies.
        tv_shows_filtered: Number of TV series entries filtered out.
        already_ranked: Number of movies the user has already ranked.
        ready_for_review: Number of movies ready for user review.
        movies: List of matched movies for the review flow.
    """

    session_id: str
    total_entries: int
    movies_found: int
    tv_shows_filtered: int
    already_ranked: int
    ready_for_review: int
    movies: list[MatchedMovieItem]


class ImportSessionDetailResponse(BaseModel):
    """Current state of an import session.

    RESPONSE SHAPE: {
        session_id: "...",
        current_index: N,
        total_movies: N,
        added_count: N,
        skipped_count: N,
        remaining_count: N,
        movies: [...]
    }

    Used to resume an import session or check progress.

    Attributes:
        session_id: Unique identifier for this import session.
        current_index: Current position in the review queue.
        total_movies: Total number of movies in the session.
        added_count: Number of movies added to rankings so far.
        skipped_count: Number of movies skipped so far.
        remaining_count: Number of movies still pending review.
        movies: List of all movies with their current statuses.
    """

    session_id: str
    current_index: int
    total_movies: int
    added_count: int
    skipped_count: int
    remaining_count: int
    movies: list[MatchedMovieItem]


class ImportMovieAddRequest(BaseModel):
    """Request to add a movie from an import session to rankings.

    Attributes:
        rating: Rating value (1-5 stars).
        rated_at: Optional date to use as rated_at (defaults to watch_date from CSV).
    """

    rating: int = Field(..., ge=1, le=5)
    rated_at: datetime | None = None


class ImportCompletionResponse(BaseModel):
    """Summary returned after completing or canceling an import.

    RESPONSE SHAPE: {
        movies_added: N,
        movies_skipped: N,
        unmatched_titles: [...]
    }

    Attributes:
        movies_added: Total number of movies added to rankings.
        movies_skipped: Total number of movies skipped by the user.
        unmatched_titles: List of movie titles that could not be matched to TMDB.
    """

    movies_added: int
    movies_skipped: int
    unmatched_titles: list[str]


class ImportMovieMatchRequest(BaseModel):
    """Request to update a movie's TMDB match in an import session.

    Used when a user manually selects a different movie from search results.
    Sets the match with 1.0 confidence (user-selected) and clears alternatives.

    Attributes:
        tmdb_id: The TMDB ID of the selected movie.
        title: Movie title from TMDB.
        year: Release year (optional).
        poster_url: Full URL to poster thumbnail (optional).
        overview: Movie synopsis/description (optional).
        genre_ids: List of TMDB genre IDs (optional).
        vote_average: TMDB user rating 0.0-10.0 (optional).
        vote_count: Number of TMDB votes (optional).
        release_date: Full release date string YYYY-MM-DD (optional).
        original_language: ISO 639-1 language code (optional).
    """

    tmdb_id: int = Field(..., description="The TMDB ID of the selected movie")
    title: str = Field(..., description="Movie title from TMDB")
    year: int | None = Field(None, description="Release year")
    poster_url: str | None = Field(None, description="Full URL to poster thumbnail")
    overview: str | None = Field(None, description="Movie synopsis/description")
    genre_ids: list[int] | None = Field(None, description="List of TMDB genre IDs")
    vote_average: float | None = Field(None, description="TMDB user rating 0.0-10.0")
    vote_count: int | None = Field(None, description="Number of TMDB votes")
    release_date: str | None = Field(None, description="Full release date YYYY-MM-DD")
    original_language: str | None = Field(None, description="ISO 639-1 language code")
