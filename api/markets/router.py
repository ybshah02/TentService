from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from api.auth.dependencies import AuthUser, require_auth
from api.schemas import (
    MarketCreate,
    MarketListResponse,
    MarketResponse,
    MarketVendorResponse,
)
from db.supabase import get_supabase

router = APIRouter(prefix="/markets", tags=["markets"])

# Pagination defaults
DEFAULT_LIMIT = 20
MAX_LIMIT = 100

# Map filter bar category to vendor DB categories
CATEGORY_MAP = {
    "Food": "Food & Beverages",
    "Art": "Art & Prints",
    "Home": "Home Goods",
}


def _resolve_category(cat: str | None) -> str | None:
    if not cat or not cat.strip() or cat.strip().lower() == "all":
        return None
    return CATEGORY_MAP.get(cat.strip(), cat.strip())


def _resolve_date_range(dr: str | None) -> tuple[date | None, date | None]:
    if not dr or not dr.strip():
        return None, None
    dr = dr.strip()
    today = date.today()
    if dr.lower() == "today":
        return today, today
    if dr.lower() == "this week":
        return today, today + timedelta(days=7)
    if dr.lower() == "this month":
        return today, today + timedelta(days=31)
    if dr.lower() == "next month":
        return today + timedelta(days=31), today + timedelta(days=62)
    return None, None


@router.get("/health")
async def markets_health():
    """Markets module health check."""
    return {"status": "ok", "module": "markets"}


@router.get("", response_model=MarketListResponse)
async def list_markets(
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    category: str | None = Query(default=None, description="Filter by vendor category"),
    date_range: str | None = Query(
        default=None,
        description="Today | This Week | This Month | Next Month | Open Today | All",
    ),
    min_vendors: int | None = Query(default=None, ge=1, le=200),
):
    """List markets with pagination and optional filters. Returns published markets."""
    supabase = get_supabase()

    cat_filter = _resolve_category(category)
    currently_open = (
        date_range
        and date_range.strip().lower()
        in ("currently open", "currently_open", "open now", "open today")
    )

    if currently_open:
        dr_start, dr_end = None, None
    else:
        dr_start, dr_end = _resolve_date_range(date_range)

    # Build base query - exclude past markets (end_date >= today)
    today = date.today().isoformat()
    query = (
        supabase.table("markets")
        .select("*", count="exact")
        .eq("is_published", True)
        .gte("end_date", today)
    )

    if min_vendors is not None:
        query = query.gte("vendor_count", min_vendors)

    if currently_open:
        # Date filter: today must fall within market dates (start_date <= today <= end_date)
        query = query.lte("start_date", today)
    elif dr_start is not None:
        query = query.gte("end_date", dr_start.isoformat())
    if dr_end is not None:
        query = query.lte("start_date", dr_end.isoformat())

    if cat_filter is not None:
        # Get market_ids that have at least one vendor in this category
        vendors_resp = (
            supabase.table("vendors")
            .select("id, categories")
            .execute()
        )
        # Filter in Python: PostgREST array contains can be finicky with text[]
        all_vendors = vendors_resp.data or []
        vendor_ids = [
            v["id"] for v in all_vendors
            if v.get("categories") and cat_filter in v["categories"]
        ]

        if not vendor_ids:
            return MarketListResponse(items=[], total=0, limit=limit, offset=offset)

        vendor_id_strs = [str(vid) for vid in vendor_ids]
        mv_resp = (
            supabase.table("market_vendors")
            .select("market_id")
            .in_("vendor_id", vendor_id_strs)
            .execute()
        )
        market_ids = list({m["market_id"] for m in (mv_resp.data or [])})

        if not market_ids:
            return MarketListResponse(items=[], total=0, limit=limit, offset=offset)

        # Ensure UUIDs as strings for PostgREST .in_() filter
        market_id_strs = [str(mid) for mid in market_ids]
        query = query.in_("id", market_id_strs)

    query = query.order("start_date", desc=False)
    if currently_open:
        # Date-only filter: show markets where today is within [start_date, end_date].
        # Time filtering skipped to avoid timezone mismatches (server UTC vs market local time).
        response = query.range(offset, offset + limit - 1).execute()
        items_raw = response.data or []
        total = response.count if response.count is not None else len(items_raw)
    else:
        response = query.range(offset, offset + limit - 1).execute()
        items_raw = response.data or []
        total = response.count if response.count is not None else len(items_raw)

    items = [MarketResponse.model_validate(row) for row in items_raw]

    return MarketListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/my", response_model=MarketListResponse)
async def list_my_markets(
    past: bool = Query(default=False, description="If true, return past markets; else upcoming"),
    user: AuthUser = Depends(require_auth),
):
    """
    List markets for the current user.
    - Vendors: markets they've joined (market_vendors)
    - Customers: markets they've marked interested (interactions)
    """
    supabase = get_supabase()
    today = date.today().isoformat()

    vendor_resp = (
        supabase.table("vendors")
        .select("id")
        .eq("profile_id", user.id)
        .execute()
    )
    is_vendor = bool(vendor_resp.data)

    if is_vendor:
        vendor_id = str(vendor_resp.data[0]["id"])
        mv_resp = (
            supabase.table("market_vendors")
            .select("market_id")
            .eq("vendor_id", vendor_id)
            .execute()
        )
        market_ids = [m["market_id"] for m in (mv_resp.data or [])]
    else:
        intr_resp = (
            supabase.table("interactions")
            .select("market_id")
            .eq("profile_id", user.id)
            .eq("type", "interested")
            .execute()
        )
        market_ids = [i["market_id"] for i in (intr_resp.data or []) if i.get("market_id")]

    if not market_ids:
        return MarketListResponse(items=[], total=0, limit=100, offset=0)

    query = (
        supabase.table("markets")
        .select("*")
        .in_("id", [str(m) for m in market_ids])
        .eq("is_published", True)
    )
    if past:
        query = query.lt("end_date", today)
    else:
        query = query.gte("end_date", today)

    query = query.order("start_date", desc=past).range(0, 99)
    response = query.execute()
    items = [MarketResponse.model_validate(row) for row in (response.data or [])]

    return MarketListResponse(
        items=items,
        total=len(items),
        limit=100,
        offset=0,
    )


@router.get("/{market_id}/vendors", response_model=list[MarketVendorResponse])
async def list_market_vendors(market_id: str):
    """List vendors participating in a market, with featured flag."""
    supabase = get_supabase()

    # Verify market exists
    market_resp = (
        supabase.table("markets")
        .select("id")
        .eq("id", market_id)
        .execute()
    )
    if not market_resp.data:
        raise HTTPException(status_code=404, detail="Market not found")

    # Join market_vendors with vendors
    mv_resp = (
        supabase.table("market_vendors")
        .select(
            "vendor_id, is_featured_at_market, vendors(id, name, slug, categories, "
            "profile_image_url, follower_count)"
        )
        .eq("market_id", market_id)
        .execute()
    )

    items = []
    for row in mv_resp.data or []:
        v = row.get("vendors") or row.get("vendor")
        if not v or not isinstance(v, dict):
            continue
        items.append(
            MarketVendorResponse(
                id=v["id"],
                name=v["name"],
                slug=v["slug"],
                categories=v.get("categories") or [],
                profile_image_url=v.get("profile_image_url"),
                follower_count=v.get("follower_count") or 0,
                is_featured_at_market=row.get("is_featured_at_market") or False,
            )
        )
    return items


@router.post("/{market_id}/join", status_code=201)
async def join_market(
    market_id: str,
    user: AuthUser = Depends(require_auth),
):
    """Vendor joins a market (adds self to market_vendors). Requires vendor authentication."""
    supabase = get_supabase()

    vendor_resp = (
        supabase.table("vendors")
        .select("id")
        .eq("profile_id", user.id)
        .execute()
    )
    if not vendor_resp.data:
        raise HTTPException(
            status_code=403,
            detail="Only vendors can join markets. Complete vendor onboarding first.",
        )
    vendor_id = vendor_resp.data[0]["id"]

    market_resp = (
        supabase.table("markets")
        .select("id")
        .eq("id", market_id)
        .execute()
    )
    if not market_resp.data:
        raise HTTPException(status_code=404, detail="Market not found")

    try:
        supabase.table("market_vendors").insert({
            "market_id": market_id,
            "vendor_id": str(vendor_id),
        }).execute()
    except Exception as e:
        err = str(e).lower()
        if "duplicate" in err or "unique" in err or "already exists" in err:
            raise HTTPException(
                status_code=409,
                detail="Vendor is already signed up for this market",
            ) from e
        raise HTTPException(status_code=500, detail="Failed to join market") from e

    return {"ok": True, "message": "Joined market successfully"}


@router.delete("/{market_id}/join", status_code=200)
async def leave_market(
    market_id: str,
    user: AuthUser = Depends(require_auth),
):
    """Vendor leaves a market (removes from market_vendors)."""
    supabase = get_supabase()

    vendor_resp = (
        supabase.table("vendors")
        .select("id")
        .eq("profile_id", user.id)
        .execute()
    )
    if not vendor_resp.data:
        raise HTTPException(status_code=403, detail="Only vendors can leave markets.")
    vendor_id = str(vendor_resp.data[0]["id"])

    result = (
        supabase.table("market_vendors")
        .delete()
        .eq("market_id", market_id)
        .eq("vendor_id", vendor_id)
        .execute()
    )
    if not result.data and hasattr(result, "count") and result.count == 0:
        raise HTTPException(status_code=404, detail="Not signed up for this market")

    return {"ok": True, "message": "Left market successfully"}


@router.get("/{market_id}/vendor-status")
async def get_market_vendor_status(
    market_id: str,
    user: AuthUser = Depends(require_auth),
):
    """Check if the current vendor is signed up for this market. Returns 403 for non-vendors."""
    supabase = get_supabase()

    vendor_resp = (
        supabase.table("vendors")
        .select("id")
        .eq("profile_id", user.id)
        .execute()
    )
    if not vendor_resp.data:
        raise HTTPException(status_code=403, detail="Vendor profile required")

    vendor_id = str(vendor_resp.data[0]["id"])
    mv_resp = (
        supabase.table("market_vendors")
        .select("id")
        .eq("market_id", market_id)
        .eq("vendor_id", vendor_id)
        .execute()
    )
    return {"joined": bool(mv_resp.data and len(mv_resp.data) > 0)}


@router.get("/{market_id}/interested-status")
async def get_market_interested_status(
    market_id: str,
    user: AuthUser = Depends(require_auth),
):
    """Check if the current customer has marked this market as interested."""
    supabase = get_supabase()

    resp = (
        supabase.table("interactions")
        .select("id")
        .eq("profile_id", user.id)
        .eq("market_id", market_id)
        .eq("type", "interested")
        .execute()
    )
    return {"interested": bool(resp.data and len(resp.data) > 0)}


@router.post("/{market_id}/interested", status_code=201)
async def add_market_interested(
    market_id: str,
    user: AuthUser = Depends(require_auth),
):
    """Customer marks market as interested. Inserts into interactions table."""
    supabase = get_supabase()

    market_resp = (
        supabase.table("markets")
        .select("id")
        .eq("id", market_id)
        .execute()
    )
    if not market_resp.data:
        raise HTTPException(status_code=404, detail="Market not found")

    try:
        supabase.table("interactions").insert({
            "profile_id": user.id,
            "market_id": market_id,
            "type": "interested",
        }).execute()
    except Exception as e:
        err = str(e).lower()
        if "duplicate" in err or "unique" in err or "already exists" in err:
            return {"ok": True, "message": "Already interested"}
        raise HTTPException(status_code=500, detail="Failed to add interest") from e

    return {"ok": True, "message": "Marked as interested"}


@router.delete("/{market_id}/interested", status_code=200)
async def remove_market_interested(
    market_id: str,
    user: AuthUser = Depends(require_auth),
):
    """Customer removes interested status from market."""
    supabase = get_supabase()

    result = (
        supabase.table("interactions")
        .delete()
        .eq("profile_id", user.id)
        .eq("market_id", market_id)
        .eq("type", "interested")
        .execute()
    )
    return {"ok": True, "message": "Removed interest"}


@router.get("/{market_id}", response_model=MarketResponse)
async def get_market(market_id: str):
    """Get a single market by ID."""
    supabase = get_supabase()

    response = (
        supabase.table("markets")
        .select("*")
        .eq("id", market_id)
        .execute()
    )

    if not response.data or len(response.data) == 0:
        raise HTTPException(status_code=404, detail="Market not found")

    return MarketResponse.model_validate(response.data[0])


@router.post("", response_model=MarketResponse, status_code=201)
async def create_market(
    body: MarketCreate,
    user: AuthUser = Depends(require_auth),
):
    """Create a new market. Requires authentication."""
    supabase = get_supabase()

    payload = body.model_dump(mode="json")

    response = supabase.table("markets").insert(payload).execute()

    if not response.data or len(response.data) == 0:
        raise HTTPException(status_code=500, detail="Failed to create market")

    return MarketResponse.model_validate(response.data[0])
