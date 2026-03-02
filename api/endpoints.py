"""Central API spec - includes all routers from api subfolders."""
from fastapi import APIRouter

from api.auth.router import router as auth_router
from api.debug.router import router as debug_router
from api.markets.router import router as markets_router
from api.posts.router import router as posts_router
from api.profile.router import router as profile_router
from api.search.router import router as search_router
from api.vendors.router import router as vendors_router
from utils.config import get_settings

api_router = APIRouter()

# Include all feature routers
api_router.include_router(auth_router)
if get_settings().debug_routes_enabled:
    api_router.include_router(debug_router)
api_router.include_router(markets_router)
api_router.include_router(posts_router)
api_router.include_router(profile_router)
api_router.include_router(search_router)
api_router.include_router(vendors_router)
