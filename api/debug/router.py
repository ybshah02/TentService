"""Debug API - create markets, vendor signups (pre-launch aggregation)."""

from datetime import date, time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from api.auth.dependencies import AuthUser, require_auth
from db.supabase import get_supabase

router = APIRouter(prefix="/debug", tags=["debug"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class DebugMarketCreate(BaseModel):
    """Create market (debug) - uses first admin if current user is not admin."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    location_name: str = Field(..., min_length=1, max_length=255)
    location_address: str | None = None
    location_city: str | None = None
    location_state: str | None = None
    location_lat: float | None = None
    location_lng: float | None = None
    start_date: date
    end_date: date
    start_time: str | None = None  # "09:00"
    end_time: str | None = None
    image_url: str | None = None
    is_published: bool = False


class VendorSignupCreate(BaseModel):
    """Vendor signup - pre-launch aggregation. No password; invite via forgot-password later."""

    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    categories: list[str] = Field(default_factory=list)
    profile_image_url: str | None = None
    gallery_images: list[str] = Field(default_factory=list)
    market_ids: list[str] = Field(default_factory=list, description="Markets this vendor will be at")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_admin_id(sb, user_id: str) -> str:
    """Get admin_id for market creation. Requires current user to be an admin."""
    admin_row = sb.table("admins").select("id").eq("profile_id", user_id).execute()
    if not admin_row.data or len(admin_row.data) == 0:
        raise HTTPException(
            status_code=403,
            detail="Admin role required to create markets. Only admins can create markets.",
        )
    return str(admin_row.data[0]["id"])


def _to_time(s: str | None) -> time | None:
    """Parse HH:MM or HH:MM:SS to time."""
    if not s or not s.strip():
        return None
    parts = s.strip().split(":")
    if len(parts) >= 2:
        try:
            h, m = int(parts[0]), int(parts[1])
            if 0 <= h <= 23 and 0 <= m <= 59:
                return time(hour=h, minute=m)
        except ValueError:
            pass
    return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/markets")
async def debug_create_market(
    body: DebugMarketCreate,
    auth: AuthUser = Depends(require_auth),
):
    """Create a market. Requires current user to be an admin."""
    sb = get_supabase()
    admin_id = _resolve_admin_id(sb, auth.id)

    payload = {
        "admin_id": admin_id,
        "name": body.name,
        "slug": body.slug,
        "description": body.description,
        "location_name": body.location_name,
        "location_address": body.location_address,
        "location_city": body.location_city,
        "location_state": body.location_state,
        "location_lat": body.location_lat,
        "location_lng": body.location_lng,
        "start_date": body.start_date.isoformat(),
        "end_date": body.end_date.isoformat(),
        "start_time": _to_time(body.start_time).isoformat() if body.start_time else None,
        "end_time": _to_time(body.end_time).isoformat() if body.end_time else None,
        "image_url": body.image_url,
        "is_published": body.is_published,
    }

    resp = sb.table("markets").insert(payload).execute()
    if not resp.data or len(resp.data) == 0:
        raise HTTPException(status_code=500, detail="Failed to create market")
    return resp.data[0]


@router.post("/vendor-signups")
async def debug_create_vendor_signup(body: VendorSignupCreate):
    """Create a vendor signup (pre-launch aggregation). No auth required."""
    sb = get_supabase()

    signup_row = (
        sb.table("vendor_signups")
        .insert(
            {
                "email": body.email,
                "name": body.name,
                "description": body.description or None,
                "categories": body.categories or [],
                "profile_image_url": body.profile_image_url or None,
                "gallery_images": body.gallery_images or [],
            }
        )
        .execute()
    )

    if not signup_row.data or len(signup_row.data) == 0:
        raise HTTPException(status_code=500, detail="Failed to create vendor signup")
    signup_id = str(signup_row.data[0]["id"])

    if body.market_ids:
        for mid in body.market_ids:
            if mid:
                sb.table("vendor_signup_markets").insert(
                    {"vendor_signup_id": signup_id, "market_id": mid}
                ).execute()

    return {"id": signup_id, "email": body.email, "market_ids": body.market_ids}
