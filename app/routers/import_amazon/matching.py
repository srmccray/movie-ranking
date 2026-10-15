"""TMDB matching logic for the Amazon Prime import workflow."""

import asyncio
import logging
from difflib import SequenceMatcher
from uuid import UUID

from sqlalchemy import select

from app.database import DbSession
from app.models.movie import Movie
from app.models.ranking import Ranking
from app.schemas.import_amazon import (
    MatchedMovieItem,
    ParsedMovieItem,
    TMDBMatchResult,
)
from app.services.tmdb import TMDBRateLimitError, TMDBService

logger = logging.getLogger(__name__)


def calculate_confidence(
    parsed_title: str,
    parsed_year: int | None,
    tmdb_title: str,
    tmdb_year: int | None,
) -> float:
    """Calculate match confidence score (0.0 - 1.0).

    Uses title similarity (60% weight) and year match (40% weight).

    Args:
        parsed_title: Title from Amazon Prime CSV.
        parsed_year: Year extracted from watch date (optional).
        tmdb_title: Title from TMDB search result.
        tmdb_year: Release year from TMDB (optional).

    Returns:
        Confidence score between 0.0 and 1.0.
    """
    score = 0.0

    # Title similarity (0.0 - 0.6)
    title_ratio = SequenceMatcher(
        None,
        parsed_title.lower(),
        tmdb_title.lower(),
    ).ratio()
    score += title_ratio * 0.6

    # Year match (0.0 - 0.4)
    if parsed_year and tmdb_year:
        if parsed_year == tmdb_year:
            score += 0.4
        elif abs(parsed_year - tmdb_year) == 1:
            score += 0.2  # Off by one year, still likely correct

    return min(score, 1.0)


async def match_movies_with_tmdb(
    parsed_movies: list,
    user_id: UUID,
    db: DbSession,
) -> tuple[list[MatchedMovieItem], int]:
    """Match parsed movies against TMDB with rate limiting.

    Args:
        parsed_movies: List of ParsedMovie objects from CSV parser.
        user_id: Current user's ID for checking existing rankings.
        db: Database session.

    Returns:
        Tuple of (matched movies list, already_ranked count).
    """
    matched: list[MatchedMovieItem] = []
    already_ranked = 0

    # Get user's existing ranked movie TMDB IDs
    existing_result = await db.execute(
        select(Movie.tmdb_id)
        .join(Ranking, Ranking.movie_id == Movie.id)
        .where(Ranking.user_id == user_id)
    )
    existing_tmdb_ids = set(row[0] for row in existing_result.all())

    async with TMDBService() as service:
        for i, movie in enumerate(parsed_movies):
            try:
                # Rate limiting: delay every 35 requests
                if i > 0 and i % 35 == 0:
                    await asyncio.sleep(1.0)

                results = await service.search_movies(
                    query=movie.title,
                    year=movie.year,
                )

                if results:
                    best_match = results[0]
                    confidence = calculate_confidence(
                        movie.title,
                        movie.year,
                        best_match.title,
                        best_match.year,
                    )

                    # Check if already ranked
                    if best_match.tmdb_id in existing_tmdb_ids:
                        already_ranked += 1
                        continue  # Skip already-ranked movies

                    matched.append(
                        MatchedMovieItem(
                            parsed=ParsedMovieItem(
                                title=movie.title,
                                watch_date=movie.watch_date,
                                prime_image_url=movie.prime_image_url,
                            ),
                            tmdb_match=TMDBMatchResult(
                                tmdb_id=best_match.tmdb_id,
                                title=best_match.title,
                                year=best_match.year,
                                poster_url=best_match.poster_url,
                                overview=best_match.overview,
                                genre_ids=best_match.genre_ids,
                                vote_average=best_match.vote_average,
                                vote_count=best_match.vote_count,
                                release_date=best_match.release_date,
                                original_language=best_match.original_language,
                            ),
                            confidence=confidence,
                            alternatives=[
                                TMDBMatchResult(
                                    tmdb_id=r.tmdb_id,
                                    title=r.title,
                                    year=r.year,
                                    poster_url=r.poster_url,
                                    overview=r.overview,
                                    genre_ids=r.genre_ids,
                                    vote_average=r.vote_average,
                                    vote_count=r.vote_count,
                                    release_date=r.release_date,
                                    original_language=r.original_language,
                                )
                                for r in results[1:3]  # Up to 2 alternatives
                            ],
                            status="pending",
                        )
                    )
                else:
                    # No TMDB match found
                    matched.append(
                        MatchedMovieItem(
                            parsed=ParsedMovieItem(
                                title=movie.title,
                                watch_date=movie.watch_date,
                                prime_image_url=movie.prime_image_url,
                            ),
                            tmdb_match=None,
                            confidence=0.0,
                            alternatives=[],
                            status="pending",
                        )
                    )

            except TMDBRateLimitError:
                # Wait and retry once
                logger.warning(f"Rate limited on movie {i}, waiting 2 seconds...")
                await asyncio.sleep(2.0)
                try:
                    results = await service.search_movies(query=movie.title)
                    if results:
                        best_match = results[0]
                        if best_match.tmdb_id not in existing_tmdb_ids:
                            matched.append(
                                MatchedMovieItem(
                                    parsed=ParsedMovieItem(
                                        title=movie.title,
                                        watch_date=movie.watch_date,
                                        prime_image_url=movie.prime_image_url,
                                    ),
                                    tmdb_match=TMDBMatchResult(
                                        tmdb_id=best_match.tmdb_id,
                                        title=best_match.title,
                                        year=best_match.year,
                                        poster_url=best_match.poster_url,
                                        overview=best_match.overview,
                                        genre_ids=best_match.genre_ids,
                                        vote_average=best_match.vote_average,
                                        vote_count=best_match.vote_count,
                                        release_date=best_match.release_date,
                                        original_language=best_match.original_language,
                                    ),
                                    confidence=calculate_confidence(
                                        movie.title,
                                        movie.year,
                                        best_match.title,
                                        best_match.year,
                                    ),
                                    alternatives=[],
                                    status="pending",
                                )
                            )
                        else:
                            already_ranked += 1
                    else:
                        matched.append(
                            MatchedMovieItem(
                                parsed=ParsedMovieItem(
                                    title=movie.title,
                                    watch_date=movie.watch_date,
                                    prime_image_url=movie.prime_image_url,
                                ),
                                tmdb_match=None,
                                confidence=0.0,
                                alternatives=[],
                                status="pending",
                            )
                        )
                except TMDBRateLimitError:
                    # Still rate limited, mark as unmatched
                    matched.append(
                        MatchedMovieItem(
                            parsed=ParsedMovieItem(
                                title=movie.title,
                                watch_date=movie.watch_date,
                                prime_image_url=movie.prime_image_url,
                            ),
                            tmdb_match=None,
                            confidence=0.0,
                            alternatives=[],
                            status="pending",
                        )
                    )

            except Exception as e:
                logger.error(f"Error matching movie '{movie.title}': {e}")
                matched.append(
                    MatchedMovieItem(
                        parsed=ParsedMovieItem(
                            title=movie.title,
                            watch_date=movie.watch_date,
                            prime_image_url=movie.prime_image_url,
                        ),
                        tmdb_match=None,
                        confidence=0.0,
                        alternatives=[],
                        status="pending",
                    )
                )

    return matched, already_ranked
