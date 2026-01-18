"""Tests for CSV parser service.

These tests verify the Amazon Prime CSV parsing functionality including:
- Parsing valid CSV with mixed movies and TV shows
- Handling various date formats
- Handling missing optional columns
- Handling missing required columns
- Handling empty CSV files
- Handling malformed rows (skip, continue)
- Handling non-UTF-8 encoding (Latin-1 fallback)
"""

import io
import pytest
from datetime import datetime

from app.services.csv_parser import (
    ParsedMovie,
    ParseResult,
    parse_amazon_prime_csv,
    parse_date,
)


class TestParseDate:
    """Tests for the parse_date helper function."""

    def test_parse_date_yyyy_mm_dd(self):
        """Test parsing date in YYYY-MM-DD format."""
        dt, year = parse_date("2024-01-15")
        assert dt == datetime(2024, 1, 15)
        assert year == 2024

    def test_parse_date_mm_dd_yyyy(self):
        """Test parsing date in MM/DD/YYYY format."""
        dt, year = parse_date("01/15/2024")
        assert dt == datetime(2024, 1, 15)
        assert year == 2024

    def test_parse_date_dd_mm_yyyy(self):
        """Test parsing date in DD/MM/YYYY format."""
        dt, year = parse_date("15/01/2024")
        assert dt == datetime(2024, 1, 15)
        assert year == 2024

    def test_parse_date_iso_format(self):
        """Test parsing ISO format without timezone."""
        dt, year = parse_date("2024-01-15T10:30:00")
        assert dt == datetime(2024, 1, 15, 10, 30, 0)
        assert year == 2024

    def test_parse_date_iso_format_with_z(self):
        """Test parsing ISO format with Z suffix."""
        dt, year = parse_date("2024-01-15T10:30:00Z")
        assert dt == datetime(2024, 1, 15, 10, 30, 0)
        assert year == 2024

    def test_parse_date_datetime_with_space(self):
        """Test parsing date with space separator."""
        dt, year = parse_date("2024-01-15 10:30:00")
        assert dt == datetime(2024, 1, 15, 10, 30, 0)
        assert year == 2024

    def test_parse_date_empty_string(self):
        """Test parsing empty string returns None."""
        dt, year = parse_date("")
        assert dt is None
        assert year is None

    def test_parse_date_none(self):
        """Test parsing None returns None."""
        dt, year = parse_date(None)
        assert dt is None
        assert year is None

    def test_parse_date_whitespace_only(self):
        """Test parsing whitespace-only string returns None."""
        dt, year = parse_date("   ")
        assert dt is None
        assert year is None

    def test_parse_date_strips_whitespace(self):
        """Test that whitespace is stripped before parsing."""
        dt, year = parse_date("  2024-01-15  ")
        assert dt == datetime(2024, 1, 15)
        assert year == 2024

    def test_parse_date_extracts_year_from_partial(self):
        """Test extracting year when full date parse fails but year is valid."""
        dt, year = parse_date("2024 some garbage")
        assert dt is None
        assert year == 2024

    def test_parse_date_invalid_format(self):
        """Test that completely invalid format returns None, None."""
        dt, year = parse_date("not a date")
        assert dt is None
        assert year is None

    def test_parse_date_year_out_of_range_in_fallback(self):
        """Test that year outside valid range in fallback extraction returns None."""
        # When only year extraction is attempted (not full date parsing),
        # years outside 1900-2100 are rejected
        dt, year = parse_date("1800 some garbage")
        assert dt is None
        assert year is None

    def test_parse_date_old_year_full_format_still_parses(self):
        """Test that old dates in valid formats still parse successfully."""
        # Full date parsing succeeds even for old years - the range check
        # only applies to year-only extraction fallback
        dt, year = parse_date("1800-01-01")
        assert dt == datetime(1800, 1, 1)
        assert year == 1800


class TestParseAmazonPrimeCsvValidFiles:
    """Tests for parse_amazon_prime_csv with valid CSV data."""

    def test_parse_valid_csv_with_movies_only(self):
        """Test parsing a valid CSV file containing only movies."""
        csv_content = b"""Date Watched,Type,Title,Episode Title,Global Title Identifier,Episode Global Title Identifier,Path,Episode Path,Image URL
2024-01-15,Movie,The Matrix,,abc123,,/path/1,,https://example.com/matrix.jpg
2024-02-20,Movie,Inception,,def456,,/path/2,,https://example.com/inception.jpg
"""
        file = io.BytesIO(csv_content)
        result = parse_amazon_prime_csv(file)

        assert isinstance(result, ParseResult)
        assert result.total_entries == 2
        assert result.movies_found == 2
        assert result.tv_shows_filtered == 0
        assert result.parse_errors == 0
        assert len(result.movies) == 2

        # Verify first movie
        assert result.movies[0].title == "The Matrix"
        assert result.movies[0].watch_date == datetime(2024, 1, 15)
        assert result.movies[0].year == 2024
        assert result.movies[0].prime_image_url == "https://example.com/matrix.jpg"

        # Verify second movie
        assert result.movies[1].title == "Inception"
        assert result.movies[1].watch_date == datetime(2024, 2, 20)
        assert result.movies[1].year == 2024

    def test_parse_csv_filters_tv_series(self):
        """Test that TV series entries are filtered out."""
        csv_content = b"""Date Watched,Type,Title,Episode Title,Global Title Identifier,Episode Global Title Identifier,Path,Episode Path,Image URL
2024-01-15,Movie,The Matrix,,abc123,,/path/1,,
2024-01-16,Series,Breaking Bad,Pilot,xyz789,ep001,/path/2,/path/2/ep1,
2024-01-17,Movie,Inception,,def456,,/path/3,,
2024-01-18,Series,The Office,The Pilot,uvw321,ep001,/path/4,/path/4/ep1,
"""
        file = io.BytesIO(csv_content)
        result = parse_amazon_prime_csv(file)

        assert result.total_entries == 4
        assert result.movies_found == 2
        assert result.tv_shows_filtered == 2
        assert result.parse_errors == 0
        assert len(result.movies) == 2
        assert result.movies[0].title == "The Matrix"
        assert result.movies[1].title == "Inception"

    def test_parse_csv_type_case_insensitive(self):
        """Test that Type comparison is case-insensitive."""
        csv_content = b"""Date Watched,Type,Title,Episode Title,Global Title Identifier,Episode Global Title Identifier,Path,Episode Path,Image URL
2024-01-15,movie,The Matrix,,abc123,,/path/1,,
2024-01-16,MOVIE,Inception,,def456,,/path/2,,
2024-01-17,Movie,Interstellar,,ghi789,,/path/3,,
2024-01-18,SERIES,Breaking Bad,Pilot,xyz789,ep001,/path/4,/path/4/ep1,
"""
        file = io.BytesIO(csv_content)
        result = parse_amazon_prime_csv(file)

        assert result.movies_found == 3
        assert result.tv_shows_filtered == 1

    def test_parse_csv_with_various_date_formats(self):
        """Test parsing CSV with various date formats."""
        csv_content = b"""Date Watched,Type,Title,Episode Title,Global Title Identifier,Episode Global Title Identifier,Path,Episode Path,Image URL
2024-01-15,Movie,Movie 1,,id1,,/path/1,,
01/20/2024,Movie,Movie 2,,id2,,/path/2,,
2024-03-25T14:30:00,Movie,Movie 3,,id3,,/path/3,,
"""
        file = io.BytesIO(csv_content)
        result = parse_amazon_prime_csv(file)

        assert result.movies_found == 3
        assert result.movies[0].watch_date == datetime(2024, 1, 15)
        assert result.movies[1].watch_date == datetime(2024, 1, 20)
        assert result.movies[2].watch_date == datetime(2024, 3, 25, 14, 30, 0)


class TestParseAmazonPrimeCsvOptionalColumns:
    """Tests for handling optional columns."""

    def test_parse_csv_missing_date_watched(self):
        """Test parsing CSV where Date Watched column is missing."""
        csv_content = b"""Type,Title,Episode Title,Global Title Identifier,Episode Global Title Identifier,Path,Episode Path,Image URL
Movie,The Matrix,,abc123,,/path/1,,https://example.com/matrix.jpg
"""
        file = io.BytesIO(csv_content)
        result = parse_amazon_prime_csv(file)

        assert result.movies_found == 1
        assert result.movies[0].title == "The Matrix"
        assert result.movies[0].watch_date is None
        assert result.movies[0].year is None

    def test_parse_csv_empty_date_watched(self):
        """Test parsing CSV with empty Date Watched values."""
        csv_content = b"""Date Watched,Type,Title,Episode Title,Global Title Identifier,Episode Global Title Identifier,Path,Episode Path,Image URL
,Movie,The Matrix,,abc123,,/path/1,,
2024-01-15,Movie,Inception,,def456,,/path/2,,
"""
        file = io.BytesIO(csv_content)
        result = parse_amazon_prime_csv(file)

        assert result.movies_found == 2
        assert result.movies[0].watch_date is None
        assert result.movies[0].year is None
        assert result.movies[1].watch_date == datetime(2024, 1, 15)

    def test_parse_csv_missing_image_url(self):
        """Test parsing CSV where Image URL column is missing."""
        csv_content = b"""Date Watched,Type,Title,Episode Title,Global Title Identifier,Episode Global Title Identifier,Path,Episode Path
2024-01-15,Movie,The Matrix,,abc123,,/path/1,
"""
        file = io.BytesIO(csv_content)
        result = parse_amazon_prime_csv(file)

        assert result.movies_found == 1
        assert result.movies[0].prime_image_url is None

    def test_parse_csv_empty_image_url(self):
        """Test parsing CSV with empty Image URL values."""
        csv_content = b"""Date Watched,Type,Title,Episode Title,Global Title Identifier,Episode Global Title Identifier,Path,Episode Path,Image URL
2024-01-15,Movie,The Matrix,,abc123,,/path/1,,
2024-01-16,Movie,Inception,,def456,,/path/2,,https://example.com/inception.jpg
"""
        file = io.BytesIO(csv_content)
        result = parse_amazon_prime_csv(file)

        assert result.movies[0].prime_image_url is None
        assert result.movies[1].prime_image_url == "https://example.com/inception.jpg"


class TestParseAmazonPrimeCsvMissingRequiredColumns:
    """Tests for handling missing required columns."""

    def test_parse_csv_missing_type_column(self):
        """Test that CSV missing Type column returns error."""
        csv_content = b"""Date Watched,Title,Episode Title,Global Title Identifier
2024-01-15,The Matrix,,abc123
"""
        file = io.BytesIO(csv_content)
        result = parse_amazon_prime_csv(file)

        assert result.total_entries == 0
        assert result.movies_found == 0
        assert result.parse_errors == 1
        assert len(result.movies) == 0

    def test_parse_csv_missing_title_column(self):
        """Test that CSV missing Title column returns error."""
        csv_content = b"""Date Watched,Type,Episode Title,Global Title Identifier
2024-01-15,Movie,,abc123
"""
        file = io.BytesIO(csv_content)
        result = parse_amazon_prime_csv(file)

        assert result.total_entries == 0
        assert result.movies_found == 0
        assert result.parse_errors == 1

    def test_parse_csv_missing_both_required_columns(self):
        """Test that CSV missing both required columns returns error."""
        csv_content = b"""Date Watched,Episode Title,Global Title Identifier
2024-01-15,,abc123
"""
        file = io.BytesIO(csv_content)
        result = parse_amazon_prime_csv(file)

        assert result.parse_errors == 1
        assert len(result.movies) == 0


class TestParseAmazonPrimeCsvEmptyFiles:
    """Tests for handling empty CSV files."""

    def test_parse_empty_file(self):
        """Test parsing a completely empty file."""
        file = io.BytesIO(b"")
        result = parse_amazon_prime_csv(file)

        assert result.total_entries == 0
        assert result.movies_found == 0
        assert result.tv_shows_filtered == 0
        assert result.parse_errors == 0
        assert len(result.movies) == 0

    def test_parse_whitespace_only_file(self):
        """Test parsing a file with only whitespace."""
        file = io.BytesIO(b"   \n\n   ")
        result = parse_amazon_prime_csv(file)

        assert result.total_entries == 0
        assert result.movies_found == 0
        assert result.parse_errors == 0

    def test_parse_headers_only_file(self):
        """Test parsing a file with only headers, no data rows."""
        csv_content = b"""Date Watched,Type,Title,Episode Title,Global Title Identifier,Episode Global Title Identifier,Path,Episode Path,Image URL
"""
        file = io.BytesIO(csv_content)
        result = parse_amazon_prime_csv(file)

        assert result.total_entries == 0
        assert result.movies_found == 0
        assert result.tv_shows_filtered == 0
        assert result.parse_errors == 0


class TestParseAmazonPrimeCsvMalformedRows:
    """Tests for handling malformed rows."""

    def test_parse_csv_skips_empty_title(self):
        """Test that rows with empty titles are skipped."""
        csv_content = b"""Date Watched,Type,Title,Episode Title,Global Title Identifier,Episode Global Title Identifier,Path,Episode Path,Image URL
2024-01-15,Movie,,,abc123,,/path/1,,
2024-01-16,Movie,The Matrix,,def456,,/path/2,,
2024-01-17,Movie,   ,,ghi789,,/path/3,,
"""
        file = io.BytesIO(csv_content)
        result = parse_amazon_prime_csv(file)

        assert result.total_entries == 3
        assert result.movies_found == 1
        assert result.parse_errors == 2
        assert result.movies[0].title == "The Matrix"

    def test_parse_csv_continues_after_malformed_row(self):
        """Test that parsing continues after encountering malformed rows."""
        csv_content = b"""Date Watched,Type,Title,Episode Title,Global Title Identifier,Episode Global Title Identifier,Path,Episode Path,Image URL
2024-01-15,Movie,First Movie,,id1,,/path/1,,
,Movie,,,id2,,/path/2,,
2024-01-17,Movie,Third Movie,,id3,,/path/3,,
"""
        file = io.BytesIO(csv_content)
        result = parse_amazon_prime_csv(file)

        assert result.total_entries == 3
        assert result.movies_found == 2
        assert result.parse_errors == 1
        assert result.movies[0].title == "First Movie"
        assert result.movies[1].title == "Third Movie"


class TestParseAmazonPrimeCsvEncoding:
    """Tests for handling different file encodings."""

    def test_parse_utf8_encoded_file(self):
        """Test parsing UTF-8 encoded file with special characters."""
        csv_content = """Date Watched,Type,Title,Episode Title,Global Title Identifier,Episode Global Title Identifier,Path,Episode Path,Image URL
2024-01-15,Movie,Le Fabuleux Destin d'Amelie Poulain,,id1,,/path/1,,
2024-01-16,Movie,Crouching Tiger Hidden Dragon \u5367\u864e\u85cf\u9f99,,id2,,/path/2,,
""".encode(
            "utf-8"
        )
        file = io.BytesIO(csv_content)
        result = parse_amazon_prime_csv(file)

        assert result.movies_found == 2
        assert "Amelie" in result.movies[0].title
        assert "\u5367\u864e\u85cf\u9f99" in result.movies[1].title  # Chinese characters

    def test_parse_latin1_encoded_file(self):
        """Test parsing Latin-1 encoded file (Windows export fallback)."""
        csv_content = """Date Watched,Type,Title,Episode Title,Global Title Identifier,Episode Global Title Identifier,Path,Episode Path,Image URL
2024-01-15,Movie,Caf\xe9 Society,,id1,,/path/1,,
2024-01-16,Movie,Na\xefve,,id2,,/path/2,,
""".encode(
            "latin-1"
        )
        file = io.BytesIO(csv_content)
        result = parse_amazon_prime_csv(file)

        assert result.movies_found == 2
        assert "Cafe" in result.movies[0].title or "Caf" in result.movies[0].title
        assert "Na" in result.movies[1].title


class TestParseAmazonPrimeCsvStatistics:
    """Tests for accurate statistics reporting."""

    def test_statistics_accuracy(self):
        """Test that all statistics are accurately reported."""
        csv_content = b"""Date Watched,Type,Title,Episode Title,Global Title Identifier,Episode Global Title Identifier,Path,Episode Path,Image URL
2024-01-15,Movie,Movie 1,,id1,,/path/1,,
2024-01-16,Series,Series 1,Ep1,id2,ep2,/path/2,/path/2/ep,
2024-01-17,Movie,Movie 2,,id3,,/path/3,,
2024-01-18,Series,Series 2,Ep1,id4,ep4,/path/4,/path/4/ep,
2024-01-19,Movie,Movie 3,,id5,,/path/5,,
,Movie,,,id6,,/path/6,,
2024-01-21,TV Show,Show 1,Ep1,id7,ep7,/path/7,/path/7/ep,
"""
        file = io.BytesIO(csv_content)
        result = parse_amazon_prime_csv(file)

        assert result.total_entries == 7
        assert result.movies_found == 3
        assert result.tv_shows_filtered == 3  # Series + TV Show entries
        assert result.parse_errors == 1  # Empty title row


class TestParsedMovieDataclass:
    """Tests for ParsedMovie dataclass."""

    def test_parsed_movie_all_fields(self):
        """Test ParsedMovie with all fields."""
        movie = ParsedMovie(
            title="The Matrix",
            watch_date=datetime(2024, 1, 15),
            year=2024,
            prime_image_url="https://example.com/matrix.jpg",
        )

        assert movie.title == "The Matrix"
        assert movie.watch_date == datetime(2024, 1, 15)
        assert movie.year == 2024
        assert movie.prime_image_url == "https://example.com/matrix.jpg"

    def test_parsed_movie_optional_fields_none(self):
        """Test ParsedMovie with optional fields as None."""
        movie = ParsedMovie(
            title="The Matrix",
            watch_date=None,
            year=None,
            prime_image_url=None,
        )

        assert movie.title == "The Matrix"
        assert movie.watch_date is None
        assert movie.year is None
        assert movie.prime_image_url is None


class TestParseResultDataclass:
    """Tests for ParseResult dataclass."""

    def test_parse_result_all_fields(self):
        """Test ParseResult with all fields."""
        movies = [
            ParsedMovie(
                title="The Matrix",
                watch_date=datetime(2024, 1, 15),
                year=2024,
                prime_image_url=None,
            )
        ]
        result = ParseResult(
            movies=movies,
            total_entries=10,
            movies_found=5,
            tv_shows_filtered=4,
            parse_errors=1,
        )

        assert len(result.movies) == 1
        assert result.total_entries == 10
        assert result.movies_found == 5
        assert result.tv_shows_filtered == 4
        assert result.parse_errors == 1

    def test_parse_result_empty(self):
        """Test ParseResult with empty/zero values."""
        result = ParseResult(
            movies=[],
            total_entries=0,
            movies_found=0,
            tv_shows_filtered=0,
            parse_errors=0,
        )

        assert result.movies == []
        assert result.total_entries == 0
        assert result.movies_found == 0
        assert result.tv_shows_filtered == 0
        assert result.parse_errors == 0
