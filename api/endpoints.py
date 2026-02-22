"""Central API spec - includes all routers from api subfolders."""
from fastapi import APIRouter

from api.auth.router import router as auth_router
from api.debug.router import router as debug_router
from api.markets.router import router as markets_router
from api.posts.router import router as posts_router
from api.profile.router import router as profile_router

api_router = APIRouter()

# Include all feature routers
api_router.include_router(auth_router)
api_router.include_router(debug_router)
api_router.include_router(markets_router)
api_router.include_router(posts_router)
api_router.include_router(profile_router)
