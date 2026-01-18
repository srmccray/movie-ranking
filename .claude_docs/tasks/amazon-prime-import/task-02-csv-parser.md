# Task 02: CSV Parser Service

**Feature:** amazon-prime-import
**Agent:** backend-implementation
**Status:** Not Started
**Blocked By:** 01

---

## Objective

Create a service that parses Amazon Prime Video CSV exports, extracts movie data, filters out TV series, and returns structured data ready for TMDB matching.

---

## Context

Amazon Prime watch history can be exported using third-party browser extensions. The CSV format includes both movies and TV series, which need to be distinguished. The parser must handle various date formats and gracefully handle malformed data.

### Relevant FRD Sections
- FRD Appendix: "Amazon Prime CSV Format" - column definitions and examples
- FRD Section: "CSV Parsing Service" - filtering logic

### Relevant Refinement Notes
- Filter by Type column: "Movie" only, skip "Series"
- Handle multiple date formats (2024-01-15, 01/15/2024)
- Return ParsedMovieItem objects from task-01 schemas

---

## Scope

### In Scope
- Create `app/services/csv_parser.py` with Amazon Prime CSV parsing logic
- Handle various date formats for watch_date
- Filter TV series (Type != "Movie")
- Extract year from watch_date for TMDB search hints
- Handle malformed CSV rows gracefully (skip, don't fail)

### Out of Scope
- TMDB matching (handled in router/task-03)
- Session storage (task-01)
- File upload handling (task-03)

---

## Implementation Notes

### Key Files

| File | Action | Notes |
|------|--------|-------|
| `/Users/stephen/Projects/movie-ranking/app/services/csv_parser.py` | Create | CSV parsing service |

### Patterns to Follow

- Service pattern: See `/Users/stephen/Projects/movie-ranking/app/services/tmdb.py`
- Use dataclasses for internal types, convert to Pydantic schemas for API

### CSV Column Mapping

Expected columns from Amazon Prime CSV:
```
Date Watched,Type,Title,Episode Title,Global Title Identifier,Episode Global Title Identifier,Path,Episode Path,Image URL
```

| Column | Used For | Required |
|--------|----------|----------|
| Date Watched | watch_date | No (nullable) |
| Type | Filter (Movie vs Series) | Yes |
| Title | Movie title for TMDB search | Yes |
| Image URL | prime_image_url fallback | No |

### Implementation

```python
# app/services/csv_parser.py

import csv
import io
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import BinaryIO

logger = logging.getLogger(__name__)


@dataclass
class ParsedMovie:
    """Internal representation of a parsed movie from CSV."""
    title: str
    watch_date: datetime | None
    year: int | None  # Extracted from watch_date for TMDB search
    prime_image_url: str | None


@dataclass
class ParseResult:
    """Result of parsing an Amazon Prime CSV file."""
    movies: list[ParsedMovie]
    total_entries: int
    movies_found: int
    tv_shows_filtered: int
    parse_errors: int


def parse_date(date_str: str | None) -> tuple[datetime | None, int | None]:
    """Parse date string in various formats.

    Returns:
        Tuple of (datetime, year) or (None, None) if parsing fails.
    """
    if not date_str or not date_str.strip():
        return None, None

    date_str = date_str.strip()

    # Try various formats
    formats = [
        "%Y-%m-%d",      # 2024-01-15
        "%m/%d/%Y",      # 01/15/2024
        "%d/%m/%Y",      # 15/01/2024
        "%Y-%m-%dT%H:%M:%S",  # ISO format without timezone
        "%Y-%m-%dT%H:%M:%SZ", # ISO format with Z
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

    Args:
        file: Binary file object containing CSV data.

    Returns:
        ParseResult with movies and statistics.
    """
    movies: list[ParsedMovie] = []
    total_entries = 0
    tv_shows_filtered = 0
    parse_errors = 0

    try:
        # Decode file content - try UTF-8 first, then Latin-1
        try:
            content = file.read().decode('utf-8')
        except UnicodeDecodeError:
            file.seek(0)
            content = file.read().decode('latin-1')

        reader = csv.DictReader(io.StringIO(content))

        # Validate required columns
        if reader.fieldnames is None:
            logger.error("CSV file has no headers")
            return ParseResult(
                movies=[],
                total_entries=0,
                movies_found=0,
                tv_shows_filtered=0,
                parse_errors=1,
            )

        required_columns = {'Type', 'Title'}
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
                content_type = row.get('Type', '').strip()
                title = row.get('Title', '').strip()

                if not title:
                    parse_errors += 1
                    continue

                # Filter out TV series
                if content_type.lower() != 'movie':
                    tv_shows_filtered += 1
                    continue

                # Parse optional fields
                watch_date, year = parse_date(row.get('Date Watched'))
                image_url = row.get('Image URL', '').strip() or None

                movies.append(ParsedMovie(
                    title=title,
                    watch_date=watch_date,
                    year=year,
                    prime_image_url=image_url,
                ))

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
```

### Technical Decisions

- **Encoding fallback:** Try UTF-8 first, fall back to Latin-1 for Windows exports
- **Year extraction:** Extract from watch_date for TMDB search optimization
- **Graceful errors:** Skip malformed rows, don't fail entire parse
- **Case-insensitive type:** Compare Type.lower() for robustness

---

## Acceptance Criteria

- [ ] Parser correctly reads Amazon Prime CSV format
- [ ] Parser filters out TV series (Type != "Movie")
- [ ] Parser handles multiple date formats (YYYY-MM-DD, MM/DD/YYYY, etc.)
- [ ] Parser extracts year from watch_date for TMDB search hints
- [ ] Parser handles UTF-8 and Latin-1 encoded files
- [ ] Parser skips malformed rows without failing
- [ ] Parser returns accurate statistics (total, movies, filtered, errors)
- [ ] Parser returns empty result for files with missing required columns

---

## Testing Requirements

- [ ] Unit test: Parse valid CSV with mixed movies and TV shows
- [ ] Unit test: Parse CSV with various date formats
- [ ] Unit test: Handle CSV with missing optional columns (Date Watched, Image URL)
- [ ] Unit test: Handle CSV missing required columns (returns error)
- [ ] Unit test: Handle empty CSV file
- [ ] Unit test: Handle malformed rows (skip, continue)
- [ ] Unit test: Handle non-UTF-8 encoding

---

## Handoff Notes

### For Next Task (task-03)
- Call `parse_amazon_prime_csv(file)` with UploadFile.file
- Use `ParseResult.movies` list for TMDB matching
- Pass stats to session store for summary display

### Artifacts Produced
- `/Users/stephen/Projects/movie-ranking/app/services/csv_parser.py`
