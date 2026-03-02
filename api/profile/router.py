"""Profile stats, lists, and update API."""

from fastapi import APIRouter, Depends, HTTPException

from api.auth.dependencies import AuthUser, require_auth
from api.profile.schemas import ProfileMeResponse, ProfileStatsResponse, ProfileUpdateRequest
from api.schemas.vendor import MarketVendorResponse
from db.supabase import get_supabase

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/me", response_model=ProfileMeResponse)
async def get_profile_me(auth: AuthUser = Depends(require_auth)):
    """Get editable profile fields for settings."""
    supabase = get_supabase()

    profile_resp = (
        supabase.table("profiles")
        .select("role")
        .eq("id", auth.id)
        .execute()
    )
    profiles = profile_resp.data or []
    if not profiles:
        raise HTTPException(status_code=404, detail="Profile not found")

    role = profiles[0].get("role") or "customer"

    if role == "customer":
        cust_resp = (
            supabase.table("customers")
            .select("name, location_city, location_state, location_lat, location_lng, allow_location")
            .eq("profile_id", auth.id)
            .execute()
        )
        if not cust_resp.data:
            raise HTTPException(status_code=404, detail="Customer profile not found")
        c = cust_resp.data[0]
        return ProfileMeResponse(
            name=c.get("name") or "",
            role="customer",
            location_city=c.get("location_city"),
            location_state=c.get("location_state"),
            location_lat=float(c["location_lat"]) if c.get("location_lat") is not None else None,
            location_lng=float(c["location_lng"]) if c.get("location_lng") is not None else None,
            allow_location=c.get("allow_location") or False,
        )

    # Vendor
    vendor_resp = (
        supabase.table("vendors")
        .select("name")
        .eq("profile_id", auth.id)
        .execute()
    )
    if not vendor_resp.data:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    v = vendor_resp.data[0]
    return ProfileMeResponse(
        name=v.get("name") or "",
        role="vendor",
    )


@router.patch("/me", status_code=200)
async def update_profile_me(
    body: ProfileUpdateRequest,
    auth: AuthUser = Depends(require_auth),
):
    """Update profile (name, location). Email/password via Supabase Auth."""
    supabase = get_supabase()

    profile_resp = (
        supabase.table("profiles")
        .select("role")
        .eq("id", auth.id)
        .execute()
    )
    profiles = profile_resp.data or []
    if not profiles:
        raise HTTPException(status_code=404, detail="Profile not found")

    role = profiles[0].get("role") or "customer"

    updates: dict = {}
    if body.name is not None:
        updates["name"] = body.name
    if role == "customer":
        if body.location_city is not None:
            updates["location_city"] = body.location_city or None
        if body.location_state is not None:
            updates["location_state"] = body.location_state or None
        if body.location_lat is not None:
            updates["location_lat"] = body.location_lat
        if body.location_lng is not None:
            updates["location_lng"] = body.location_lng
        if body.allow_location is not None:
            updates["allow_location"] = body.allow_location

    if not updates:
        return {"ok": True, "message": "Nothing to update"}

    if role == "customer":
        supabase.table("customers").update(updates).eq("profile_id", auth.id).execute()
    else:
        if "name" in updates:
            supabase.table("vendors").update({"name": updates["name"]}).eq("profile_id", auth.id).execute()
        # Vendors don't have location in settings

    return {"ok": True, "message": "Profile updated"}


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
            name=None,
            interests=[],
            vendor_id=None,
            markets_attended=0,
            followers_or_following=0,
            interested=0,
        )

    role = profiles[0].get("role") or "customer"

    # Get name and interests from customers or vendors
    name: str | None = None
    interests: list[str] = []
    if role == "customer":
        cust_resp = (
            supabase.table("customers")
            .select("name, interests")
            .eq("profile_id", auth.id)
            .execute()
        )
        if cust_resp.data and len(cust_resp.data) > 0:
            c = cust_resp.data[0]
            name = c.get("name")
            interests = c.get("interests") or []

    if role == "vendor":
        # Get vendor by profile_id
        vendor_resp = (
            supabase.table("vendors")
            .select("id, name, follower_count, interested_count")
            .eq("profile_id", auth.id)
            .execute()
        )
        vendors = vendor_resp.data or []
        if not vendors:
            return ProfileStatsResponse(
                name=None,
                interests=[],
                vendor_id=None,
                markets_attended=0,
                followers_or_following=0,
                interested=0,
            )
        v = vendors[0]
        vendor_id = v["id"]
        name = v.get("name")

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
            name=v.get("name"),
            interests=[],
            vendor_id=str(vendor_id),
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
        name=name,
        interests=interests,
        vendor_id=None,
        markets_attended=markets_interested,
        followers_or_following=vendors_following,
        interested=posts_liked,
    )


@router.get("/follow/{vendor_id}/status")
async def get_vendor_follow_status(
    vendor_id: str,
    auth: AuthUser = Depends(require_auth),
):
    """Check if the current user follows this vendor."""
    supabase = get_supabase()

    resp = (
        supabase.table("interactions")
        .select("id")
        .eq("profile_id", auth.id)
        .eq("vendor_id", vendor_id)
        .eq("type", "follow")
        .execute()
    )
    return {"following": bool(resp.data and len(resp.data) > 0)}


@router.post("/follow/{vendor_id}", status_code=201)
async def follow_vendor(
    vendor_id: str,
    auth: AuthUser = Depends(require_auth),
):
    """Customer follows a vendor. Inserts into interactions table."""
    supabase = get_supabase()

    vendor_resp = (
        supabase.table("vendors")
        .select("id")
        .eq("id", vendor_id)
        .execute()
    )
    if not vendor_resp.data:
        raise HTTPException(status_code=404, detail="Vendor not found")

    try:
        supabase.table("interactions").insert({
            "profile_id": auth.id,
            "vendor_id": vendor_id,
            "type": "follow",
        }).execute()
    except Exception as e:
        err = str(e).lower()
        if "duplicate" in err or "unique" in err or "already exists" in err:
            return {"ok": True, "message": "Already following"}
        raise HTTPException(status_code=500, detail="Failed to follow vendor") from e

    return {"ok": True, "message": "Now following"}


@router.delete("/follow/{vendor_id}", status_code=200)
async def unfollow_vendor(
    vendor_id: str,
    auth: AuthUser = Depends(require_auth),
):
    """Customer unfollows a vendor."""
    supabase = get_supabase()

    (
        supabase.table("interactions")
        .delete()
        .eq("profile_id", auth.id)
        .eq("vendor_id", vendor_id)
        .eq("type", "follow")
        .execute()
    )

    return {"ok": True, "message": "Unfollowed"}


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
