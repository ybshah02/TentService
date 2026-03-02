"""Vendors API - public vendor profile."""

from datetime import date

from fastapi import APIRouter, HTTPException

from api.schemas.market import MarketListResponse, MarketResponse
from api.schemas.vendor import VendorResponse
from db.supabase import get_supabase

router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.get("/{vendor_id}", response_model=VendorResponse)
async def get_vendor(vendor_id: str):
    """Get public vendor profile by ID."""
    supabase = get_supabase()

    resp = (
        supabase.table("vendors")
        .select("*")
        .eq("id", vendor_id)
        .execute()
    )

    if not resp.data or len(resp.data) == 0:
        raise HTTPException(status_code=404, detail="Vendor not found")

    row = resp.data[0]
    return VendorResponse.model_validate(row)


@router.get("/{vendor_id}/markets", response_model=MarketListResponse)
async def list_vendor_markets(vendor_id: str):
    """List upcoming markets the vendor is participating in."""
    supabase = get_supabase()

    mv_resp = (
        supabase.table("market_vendors")
        .select("market_id")
        .eq("vendor_id", vendor_id)
        .execute()
    )
    market_ids = [m["market_id"] for m in (mv_resp.data or []) if m.get("market_id")]
    if not market_ids:
        return MarketListResponse(items=[], total=0, limit=50, offset=0)

    today = date.today().isoformat()
    markets_resp = (
        supabase.table("markets")
        .select("*")
        .in_("id", [str(m) for m in market_ids])
        .eq("is_published", True)
        .gte("end_date", today)
        .order("start_date", desc=False)
        .limit(50)
        .execute()
    )
    items = [MarketResponse.model_validate(row) for row in (markets_resp.data or [])]
    return MarketListResponse(items=items, total=len(items), limit=50, offset=0)
