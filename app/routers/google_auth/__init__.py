"""Google OAuth router for authentication with Google accounts."""

from fastapi import APIRouter

from app.routers.google_auth import link, login

router = APIRouter(tags=["auth"])
router.include_router(login.router)
router.include_router(link.router)

__all__ = ["router"]
