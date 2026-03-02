import re

from fastapi import APIRouter, Depends

from api.auth.dependencies import require_auth
from api.auth.schemas import OnboardCustomerRequest, OnboardVendorRequest
from db.supabase import get_supabase

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/health")
async def auth_health():
    """Auth module health check."""
    return {"status": "ok", "module": "auth"}


@router.get("/me")
async def auth_me(auth=Depends(require_auth)):
    """Return current user's profile (id, role) if onboarding is complete. Used to skip onboarding on sign-in."""
    sb = get_supabase()
    resp = sb.table("profiles").select("id, role").eq("id", auth.id).execute()
    if not resp.data or len(resp.data) == 0:
        return None
    row = resp.data[0]
    return {"id": row["id"], "role": row.get("role") or "customer"}


def _slugify(name: str) -> str:
    """Convert name to URL-safe slug."""
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    return slug[:255] if slug else "vendor"


@router.post("/onboard/customer")
async def onboard_customer(
    body: OnboardCustomerRequest,
    auth=Depends(require_auth),
):
    """Create profile + customer record after signup."""
    sb = get_supabase()
    user_id = auth.id

    # Upsert profile
    sb.table("profiles").upsert(
        {
            "id": user_id,
            "role": "customer",
            "age": body.age,
            "gender": body.gender,
        },
        on_conflict="id",
    ).execute()

    # Upsert customer
    sb.table("customers").upsert(
        {
            "profile_id": user_id,
            "name": body.name,
            "location_city": body.location_city or None,
            "location_state": body.location_state or None,
            "location_lat": body.location_lat,
            "location_lng": body.location_lng,
            "allow_location": body.allow_location,
            "interests": body.interests or [],
        },
        on_conflict="profile_id",
    ).execute()

    return {"ok": True, "role": "customer"}


@router.post("/onboard/vendor")
async def onboard_vendor(
    body: OnboardVendorRequest,
    auth=Depends(require_auth),
):
    """Create profile + vendor record after signup."""
    sb = get_supabase()
    user_id = auth.id

    base_slug = _slugify(body.name)
    slug = base_slug
    n = 0
    while True:
        existing = sb.table("vendors").select("id").eq("slug", slug).execute()
        if not existing.data:
            break
        n += 1
        slug = f"{base_slug}-{n}"

    # Upsert profile
    sb.table("profiles").upsert(
        {
            "id": user_id,
            "role": "vendor",
            "age": body.age,
            "gender": body.gender,
        },
        on_conflict="id",
    ).execute()

    # Upsert vendor
    sb.table("vendors").upsert(
        {
            "profile_id": user_id,
            "name": body.name,
            "slug": slug,
            "description": body.description or None,
            "categories": body.categories or [],
            "profile_image_url": body.profile_image_url,
            "gallery_images": body.gallery_images or [],
            "instagram_handle": body.instagram_handle,
            "depop_handle": body.depop_handle,
            "tiktok_handle": body.tiktok_handle,
            "website_url": body.website_url,
        },
        on_conflict="profile_id",
    ).execute()

    return {"ok": True, "role": "vendor"}
