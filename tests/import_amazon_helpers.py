"""Shared helpers for the Amazon Prime import tests."""

import io
from unittest.mock import MagicMock


def create_test_csv(rows: list[dict]) -> io.BytesIO:
    """Create a CSV file in memory for testing.

    Args:
        rows: List of dicts with keys: Date Watched, Type, Title, Image URL

    Returns:
        BytesIO object containing CSV data.
    """
    content = "Date Watched,Type,Title,Episode Title,Global Title Identifier,Episode Global Title Identifier,Path,Episode Path,Image URL\n"
    for row in rows:
        content += f"{row.get('Date Watched', '')},{row.get('Type', 'Movie')},{row.get('Title', '')},,,,,,{row.get('Image URL', '')}\n"
    return io.BytesIO(content.encode("utf-8"))


def create_mock_tmdb_result(
    tmdb_id: int,
    title: str,
    year: int | None = None,
    poster_url: str | None = None,
    overview: str | None = None,
    genre_ids: list[int] | None = None,
    vote_average: float | None = None,
    vote_count: int | None = None,
    release_date: str | None = None,
    original_language: str | None = None,
):
    """Create a mock TMDB search result.

    All attributes must be explicitly set to avoid MagicMock returning
    nested MagicMock objects for unset attributes, which would cause
    Pydantic validation errors when creating TMDBMatchResult schemas.
    """
    mock = MagicMock()
    mock.tmdb_id = tmdb_id
    mock.title = title
    mock.year = year
    mock.poster_url = poster_url
    mock.overview = overview
    mock.genre_ids = genre_ids
    mock.vote_average = vote_average
    mock.vote_count = vote_count
    mock.release_date = release_date
    mock.original_language = original_language
    return mock
