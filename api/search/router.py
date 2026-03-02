"""Search API - markets and vendors by name."""

import math

from fastapi import APIRouter, Query

from api.schemas import MarketResponse, MarketVendorResponse
from db.supabase import get_supabase

router = APIRouter(prefix="/search", tags=["search"])

DEFAULT_LIMIT = 10
MAX_LIMIT = 50


def _haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return distance in miles between two points (Haversine formula)."""
    R = 3959  # Earth radius in miles
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


@router.get("")
async def search(
    q: str = Query(..., min_length=1, max_length=100, description="Search by market or vendor name"),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Items per page for each type"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    lat: float | None = Query(default=None, description="User latitude for distance filter on markets"),
    lng: float | None = Query(default=None, description="User longitude for distance filter on markets"),
    radius_miles: float | None = Query(default=50, ge=1, le=500, description="Max distance in miles from user"),
):
    """Search markets and vendors by name. Returns paginated results for both."""
    supabase = get_supabase()
    term = q.strip()
    if not term:
        return {
            "markets": [],
            "vendors": [],
            "markets_total": 0,
            "vendors_total": 0,
            "limit": limit,
            "offset": offset,
        }

    like_pattern = f"%{term}%"

    # Search markets by name (case-insensitive partial match)
    use_location_filter = lat is not None and lng is not None and radius_miles is not None

    markets_query = (
        supabase.table("markets")
        .select("*", count="exact")
        .eq("is_published", True)
        .ilike("name", like_pattern)
        .order("start_date", desc=False)
    )
    if use_location_filter:
        markets_resp = markets_query.range(0, 999).execute()
        all_markets = [MarketResponse.model_validate(row) for row in (markets_resp.data or [])]
        filtered = [
            m for m in all_markets
            if m.location_lat is not None and m.location_lng is not None
            and _haversine_miles(lat, lng, float(m.location_lat), float(m.location_lng)) <= radius_miles
        ]
        markets_total = len(filtered)
        markets = filtered[offset : offset + limit]
    else:
        markets_resp = markets_query.range(offset, offset + limit - 1).execute()
        markets = [MarketResponse.model_validate(row) for row in (markets_resp.data or [])]
        markets_total = getattr(markets_resp, "count", None) or len(markets)

    # Search vendors by name (case-insensitive partial match) with count
    vendors_query = (
        supabase.table("vendors")
        .select("id, name, slug, categories, profile_image_url, follower_count", count="exact")
        .ilike("name", like_pattern)
        .order("name", desc=False)
    )
    vendors_resp = vendors_query.range(offset, offset + limit - 1).execute()

    vendors = []
    for row in vendors_resp.data or []:
        vendors.append(
            MarketVendorResponse(
                id=row["id"],
                name=row["name"],
                slug=row["slug"],
                categories=row.get("categories") or [],
                profile_image_url=row.get("profile_image_url"),
                follower_count=row.get("follower_count") or 0,
                is_featured_at_market=False,
            )
        )
    vendors_total = getattr(vendors_resp, "count", None) or len(vendors)

    return {
        "markets": markets,
        "vendors": vendors,
        "markets_total": markets_total,
        "vendors_total": vendors_total,
        "limit": limit,
        "offset": offset,
    }
