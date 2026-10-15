"""Amazon Prime import router package.

Multi-step import workflow for Amazon Prime Video watch history CSV exports.
Mounted at /api/v1/import; only ``router`` is public.
"""

from fastapi import APIRouter

from . import review, session

router = APIRouter(tags=["import"])
router.include_router(session.router)
router.include_router(review.router)

__all__ = ["router"]
