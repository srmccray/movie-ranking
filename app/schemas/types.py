"""Shared annotated types for Pydantic schemas."""

from datetime import datetime, timezone
from typing import Annotated

from pydantic import AfterValidator


def _as_utc(v: datetime) -> datetime:
    """Return v as a UTC-aware datetime (naive values are labelled UTC, ADR-0010)."""
    if v.tzinfo is None:
        return v.replace(tzinfo=timezone.utc)
    return v.astimezone(timezone.utc)


UTCDatetime = Annotated[datetime, AfterValidator(_as_utc)]
"""Response datetime that always serializes as UTC-aware ISO 8601 (...Z)."""
