"""Profile stats and lists API."""

from fastapi import APIRouter, Depends, HTTPException

from api.auth.dependencies import AuthUser, require_auth
from api.profile.schemas import ProfileStatsResponse
from api.schemas.vendor import MarketVendorResponse
from db.supabase import get_supabase

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/stats", response_model=ProfileStatsResponse)
async def get_profile_stats(auth: AuthUser = Depends(require_auth)):
    """Get profile stats (markets attended, followers/following, interested) for current user."""
    supabase = get_supabase()

    # Get profile role
    profile_resp = (
        supabase.table("profiles")
        .select("role")
        .eq("id", auth.id)
        .execute()
    )
    profiles = profile_resp.data or []
    if not profiles:
        return ProfileStatsResponse(
            markets_attended=0,
            followers_or_following=0,
            interested=0,
        )

    role = profiles[0].get("role") or "customer"

    if role == "vendor":
        # Get vendor by profile_id
        vendor_resp = (
            supabase.table("vendors")
            .select("id, follower_count, interested_count")
            .eq("profile_id", auth.id)
            .execute()
        )
        vendors = vendor_resp.data or []
        if not vendors:
            return ProfileStatsResponse(
                markets_attended=0,
                followers_or_following=0,
                interested=0,
            )
        v = vendors[0]
        vendor_id = v["id"]

        # Markets attended = count of market_vendors for this vendor
        mv_resp = (
            supabase.table("market_vendors")
            .select("*", count="exact")
            .eq("vendor_id", vendor_id)
            .range(0, 0)
            .execute()
        )
        markets_attended = getattr(mv_resp, "count", None) or 0

        return ProfileStatsResponse(
            markets_attended=markets_attended,
            followers_or_following=v.get("follower_count") or 0,
            interested=v.get("interested_count") or 0,
        )

    # Customer
    # Vendors following = interactions with type=follow (vendor_id set by schema)
    follow_resp = (
        supabase.table("interactions")
        .select("*", count="exact")
        .eq("profile_id", auth.id)
        .eq("type", "follow")
        .range(0, 0)
        .execute()
    )
    vendors_following = getattr(follow_resp, "count", None) or 0

    # Markets interested in = interactions with type=interested and market_id set
    int_resp = (
        supabase.table("interactions")
        .select("*", count="exact")
        .eq("profile_id", auth.id)
        .eq("type", "interested")
        .not_.is_("market_id", "null")
        .range(0, 0)
        .execute()
    )
    markets_interested = getattr(int_resp, "count", None) or 0

    # Posts liked = interactions with type=like
    like_resp = (
        supabase.table("interactions")
        .select("*", count="exact")
        .eq("profile_id", auth.id)
        .eq("type", "like")
        .range(0, 0)
        .execute()
    )
    posts_liked = getattr(like_resp, "count", None) or 0

    return ProfileStatsResponse(
        markets_attended=markets_interested,
        followers_or_following=vendors_following,
        interested=posts_liked,
    )


@router.get("/following-vendors", response_model=list[MarketVendorResponse])
async def list_following_vendors(auth: AuthUser = Depends(require_auth)):
    """List vendors the current user (customer) follows."""
    supabase = get_supabase()

    intr_resp = (
        supabase.table("interactions")
        .select("vendor_id")
        .eq("profile_id", auth.id)
        .eq("type", "follow")
        .execute()
    )
    vendor_ids = [i["vendor_id"] for i in (intr_resp.data or []) if i.get("vendor_id")]

    if not vendor_ids:
        return []

    vendors_resp = (
        supabase.table("vendors")
        .select("id, name, slug, categories, profile_image_url, follower_count")
        .in_("id", [str(v) for v in vendor_ids])
        .execute()
    )

    items = []
    for row in vendors_resp.data or []:
        items.append(
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
    return items
