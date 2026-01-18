"""CSV parser service for Amazon Prime Video watch history imports.

This module provides functionality to parse Amazon Prime Video CSV exports,
extract movie data, filter out TV series, and return structured data ready
for TMDB matching.

Amazon Prime CSV Format:
    Date Watched,Type,Title,Episode Title,Global Title Identifier,
    Episode Global Title Identifier,Path,Episode Path,Image URL
"""

import csv
import io
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import BinaryIO

logger = logging.getLogger(__name__)


@dataclass
class ParsedMovie:
    """Internal representation of a movie parsed from CSV.

    Attributes:
        title: Movie title from the CSV.
        watch_date: Date the movie was watched (optional).
        year: Year extracted from watch_date for TMDB search hints (optional).
        prime_image_url: Amazon Prime poster/thumbnail URL (optional).
    """

    title: str
    watch_date: datetime | None
    year: int | None
    prime_image_url: str | None


@dataclass
class ParseResult:
    """Result of parsing an Amazon Prime CSV file.

    Attributes:
        movies: List of parsed movie entries.
        total_entries: Total number of rows processed from the CSV.
        movies_found: Number of entries identified as movies.
        tv_shows_filtered: Number of TV series entries filtered out.
        parse_errors: Number of rows that failed to parse.
    """

    movies: list[ParsedMovie]
    total_entries: int
    movies_found: int
    tv_shows_filtered: int
    parse_errors: int


def parse_date(date_str: str | None) -> tuple[datetime | None, int | None]:
    """Parse date string in various formats.

    Attempts to parse the date string using common date formats.
    Falls back to extracting just the year if full parsing fails.

    Args:
        date_str: Date string to parse (e.g., "2024-01-15", "01/15/2024").

    Returns:
        Tuple of (datetime, year) if successfully parsed, or (None, year)
        if only year could be extracted, or (None, None) if parsing fails.
    """
    if not date_str or not date_str.strip():
        return None, None

    date_str = date_str.strip()

    # Try various formats commonly used in CSV exports
    formats = [
        "%Y-%m-%d",  # 2024-01-15
        "%m/%d/%Y",  # 01/15/2024
        "%d/%m/%Y",  # 15/01/2024
        "%Y-%m-%dT%H:%M:%S",  # ISO format without timezone
        "%Y-%m-%dT%H:%M:%SZ",  # ISO format with Z
        "%Y-%m-%d %H:%M:%S",  # 2024-01-15 10:30:00
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt, dt.year
        except ValueError:
            continue

    # Try to extract just the year if full parse fails
    try:
        year = int(date_str[:4])
        if 1900 <= year <= 2100:
            return None, year
    except (ValueError, IndexError):
        pass

    logger.warning(f"Could not parse date: {date_str}")
    return None, None


def parse_amazon_prime_csv(file: BinaryIO) -> ParseResult:
    """Parse an Amazon Prime Video watch history CSV file.

    Reads the CSV file, filters for movies (excluding TV series),
    and extracts relevant fields for TMDB matching.

    Args:
        file: Binary file object containing CSV data.

    Returns:
        ParseResult with list of movies and parsing statistics.

    Note:
        - Tries UTF-8 encoding first, falls back to Latin-1 for Windows exports
        - Skips rows with empty titles or missing required columns
        - Filters out entries where Type is not "Movie" (case-insensitive)
        - Returns empty result with parse_errors=1 if file cannot be read
    """
    movies: list[ParsedMovie] = []
    total_entries = 0
    tv_shows_filtered = 0
    parse_errors = 0

    try:
        # Decode file content - try UTF-8 first, then Latin-1 for Windows exports
        try:
            content = file.read().decode("utf-8")
        except UnicodeDecodeError:
            file.seek(0)
            content = file.read().decode("latin-1")

        # Handle empty file
        if not content.strip():
            logger.warning("CSV file is empty")
            return ParseResult(
                movies=[],
                total_entries=0,
                movies_found=0,
                tv_shows_filtered=0,
                parse_errors=0,
            )

        reader = csv.DictReader(io.StringIO(content))

        # Validate required columns exist
        if reader.fieldnames is None:
            logger.error("CSV file has no headers")
            return ParseResult(
                movies=[],
                total_entries=0,
                movies_found=0,
                tv_shows_filtered=0,
                parse_errors=1,
            )

        required_columns = {"Type", "Title"}
        missing = required_columns - set(reader.fieldnames)
        if missing:
            logger.error(f"CSV missing required columns: {missing}")
            return ParseResult(
                movies=[],
                total_entries=0,
                movies_found=0,
                tv_shows_filtered=0,
                parse_errors=1,
            )

        for row in reader:
            total_entries += 1

            try:
                # Get required fields
                content_type = row.get("Type", "").strip()
                title = row.get("Title", "").strip()

                if not title:
                    parse_errors += 1
                    logger.debug(f"Row {total_entries}: Empty title, skipping")
                    continue

                # Filter out TV series (case-insensitive comparison)
                if content_type.lower() != "movie":
                    tv_shows_filtered += 1
                    continue

                # Parse optional fields
                watch_date, year = parse_date(row.get("Date Watched"))
                image_url = row.get("Image URL", "").strip() or None

                movies.append(
                    ParsedMovie(
                        title=title,
                        watch_date=watch_date,
                        year=year,
                        prime_image_url=image_url,
                    )
                )

            except Exception as e:
                logger.warning(f"Error parsing row {total_entries}: {e}")
                parse_errors += 1
                continue

    except Exception as e:
        logger.error(f"Error reading CSV file: {e}")
        return ParseResult(
            movies=[],
            total_entries=0,
            movies_found=0,
            tv_shows_filtered=0,
            parse_errors=1,
        )

    return ParseResult(
        movies=movies,
        total_entries=total_entries,
        movies_found=len(movies),
        tv_shows_filtered=tv_shows_filtered,
        parse_errors=parse_errors,
    )
