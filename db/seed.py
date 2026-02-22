"""
Seed script - populates database with sample data from codebase constants.

Run: python -m db.seed
Requires: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_SECRET_KEY) in .env
Optional: SEED_ADMIN_USER_ID - UUID of an existing auth user to use as admin.
          Create in Supabase Dashboard (Auth > Users) if not set; script will
          try auth.admin.create_user for seed-admin@tent.local

Uses constants from constants/categories.py - no hardcoded categories.
"""

import os
import re
import sys
from pathlib import Path
from uuid import uuid4

# Add project root (TentService) for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from constants.categories import VENDOR_CATEGORIES
from db.supabase import get_supabase
from utils.config import get_settings


def _slugify(name: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    return slug[:255] if slug else "vendor"


def _ensure_admin(sb) -> str:
    """Get or create seed admin. Returns admin table id."""
    admin_user_id = (get_settings().seed_admin_user_id or os.getenv("SEED_ADMIN_USER_ID") or "").strip()
    admin_email = "seed-admin@tent.local"
    admin_password = "SeedAdmin123!"

    if admin_user_id:
        # Use provided admin user
        sb.table("profiles").upsert(
            {"id": admin_user_id, "role": "admin"},
            on_conflict="id",
        ).execute()
    else:
        # Try auth.admin.create_user, or look up existing user
        try:
            admin = sb.auth.admin.create_user({
                "email": admin_email,
                "password": admin_password,
                "email_confirm": True,
            })
            admin_user_id = str(admin.user.id) if hasattr(admin, "user") else str(admin["id"])
        except Exception as e:
            err_msg = str(e).lower()
            if "already been registered" in err_msg or "already exists" in err_msg:
                # User exists - fetch by email
                users_resp = sb.auth.admin.list_users()
                users_list = getattr(users_resp, "users", []) or []
                for u in users_list:
                    if getattr(u, "email", "").lower() == admin_email.lower():
                        admin_user_id = str(u.id)
                        break
                if not admin_user_id:
                    raise RuntimeError(
                        f"User {admin_email} exists but could not be found. "
                        f"Set SEED_ADMIN_USER_ID in .env to their UUID."
                    ) from e
            else:
                raise RuntimeError(
                    f"Create seed admin in Supabase Dashboard (Auth > Users), "
                    f"then set SEED_ADMIN_USER_ID in .env. Error: {e}"
                ) from e
        sb.table("profiles").upsert(
            {"id": admin_user_id, "role": "admin"},
            on_conflict="id",
        ).execute()

    admin_row = sb.table("admins").select("id").eq("profile_id", admin_user_id).execute()
    if admin_row.data:
        return admin_row.data[0]["id"]
    ins = sb.table("admins").insert({
        "profile_id": admin_user_id,
        "name": "Tent Admin",
    }).execute()
    return ins.data[0]["id"]


def seed():
    sb = get_supabase()
    admin_id = _ensure_admin(sb)

    # Sample markets - Austin, TX area with geo coords for map display
    # Central Austin ~30.2672, -97.7431
    markets_data = [
        {
            "admin_id": admin_id,
            "name": "Sunday Artisan Market",
            "slug": "sunday-artisan-market",
            "description": "Vibrant celebration of local artisans and makers. Discover unique handcrafted goods.",
            "location_name": "Central Park Plaza",
            "location_address": "123 Park Avenue",
            "location_city": "Austin",
            "location_state": "TX",
            "location_lat": 30.2700,
            "location_lng": -97.7400,
            "start_date": "2026-02-16",
            "end_date": "2026-02-16",
            "start_time": "09:00",
            "end_time": "16:00",
            "image_url": "https://images.unsplash.com/photo-1739193994129-e14bc647449d?w=1080",
            "is_published": True,
        },
        {
            "admin_id": admin_id,
            "name": "Vintage Fair",
            "slug": "vintage-fair",
            "description": "Curated vintage clothing and collectibles.",
            "location_name": "Main Street",
            "location_city": "Austin",
            "location_state": "TX",
            "location_lat": 30.2650,
            "location_lng": -97.7350,
            "start_date": "2026-02-22",
            "end_date": "2026-02-23",
            "start_time": "10:00",
            "end_time": "18:00",
            "image_url": "https://images.unsplash.com/photo-1637228393246-c38a4b3d2011?w=1080",
            "is_published": True,
        },
        {
            "admin_id": admin_id,
            "name": "Farmers Market",
            "slug": "farmers-market",
            "description": "Fresh produce and local goods every Saturday.",
            "location_name": "Riverside Ave",
            "location_city": "Austin",
            "location_state": "TX",
            "location_lat": 30.2550,
            "location_lng": -97.7450,
            "start_date": "2026-02-22",
            "end_date": "2026-12-31",
            "start_time": "07:00",
            "end_time": "14:00",
            "image_url": "https://images.unsplash.com/photo-1747503331142-27f458a1498c?w=1080",
            "is_published": True,
        },
        {
            "admin_id": admin_id,
            "name": "Craft & Makers Fair",
            "slug": "craft-makers-fair",
            "description": "Handmade crafts, art, and DIY.",
            "location_name": "East Park",
            "location_city": "Austin",
            "location_state": "TX",
            "location_lat": 30.2750,
            "location_lng": -97.7250,
            "start_date": "2026-03-01",
            "end_date": "2026-03-02",
            "start_time": "11:00",
            "end_time": "19:00",
            "image_url": "https://images.unsplash.com/photo-1759719441226-349c747c9bc6?w=1080",
            "is_published": True,
        },
        {
            "admin_id": admin_id,
            "name": "Flea Market Extravaganza",
            "slug": "flea-market-extravaganza",
            "description": "Treasures and finds from local vendors.",
            "location_name": "West End",
            "location_city": "Austin",
            "location_state": "TX",
            "location_lat": 30.2600,
            "location_lng": -97.7650,
            "start_date": "2026-02-28",
            "end_date": "2026-02-28",
            "start_time": "08:00",
            "end_time": "17:00",
            "image_url": "https://images.unsplash.com/photo-1644384361176-cd4fa5548313?w=1080",
            "is_published": True,
        },
    ]

    market_ids = []
    for m in markets_data:
        r = sb.table("markets").upsert(m, on_conflict="slug").execute()
        market_ids.append(r.data[0]["id"])

    # Clear existing market_vendors for these markets (for re-seed idempotency)
    for mid in market_ids:
        sb.table("market_vendors").delete().eq("market_id", mid).execute()

    # Create vendor users and vendors - use categories from constants (VENDOR_CATEGORIES)
    vendor_specs = [
        ("Willow & Thread", ["Vintage", "Clothing"], 1240, True),
        ("Copper & Clay", ["Jewelry", "Crafts & DIY"], 856, True),
        ("Urban Woodworks", ["Home Goods"], 2103, False),
        ("Sweet Treats Co", ["Food & Beverages"], 542, False),
    ]
    vendor_password = "SeedVendor123!"

    def _find_user_by_email(sb_client, target_email: str) -> str | None:
        """Look up existing user by email. list_users returns List[User] directly."""
        try:
            users_list = sb_client.auth.admin.list_users(per_page=1000)
        except TypeError:
            users_list = sb_client.auth.admin.list_users()
        if not isinstance(users_list, list):
            users_list = getattr(users_list, "users", []) or []
        for u in users_list:
            if getattr(u, "email", "").lower() == target_email.lower():
                return str(u.id)
        return None

    vendor_ids = []
    for i, (name, cats, followers, _) in enumerate(vendor_specs):
        email = f"seed-vendor-{i+1}@tent.local"
        try:
            u = sb.auth.admin.create_user({
                "email": email,
                "password": vendor_password,
                "email_confirm": True,
            })
            uid = str(u.user.id) if hasattr(u, "user") else str(u["id"])
        except Exception as e:
            uid = _find_user_by_email(sb, email)
            if not uid:
                raise RuntimeError(
                    f"Vendor user {email} already exists but could not be found. "
                    f"Set up auth users in Supabase Dashboard. Original: {e}"
                ) from e
        sb.table("profiles").upsert({"id": uid, "role": "vendor"}, on_conflict="id").execute()
        slug = _slugify(name)
        existing = sb.table("vendors").select("id").eq("slug", slug).execute()
        if existing.data:
            vid = existing.data[0]["id"]
        else:
            vendor_row = sb.table("vendors").insert({
                "profile_id": uid,
                "name": name,
                "slug": slug,
                "categories": cats,
                "profile_image_url": "https://images.unsplash.com/photo-1752401984776-edc407a13e1e?w=400",
                "follower_count": followers,
                "is_featured_global": i < 2,
            }).execute()
            vid = vendor_row.data[0]["id"]
        vendor_ids.append(vid)

    # Link vendors to markets (market_vendors)
    # Assign vendors selectively so category filtering produces different results:
    # Willow=Vintage+Clothing, Copper=Jewelry+Crafts, Urban=Home, Sweet=Food&Beverages
    # Market 0 (Sunday Artisan): all - Market 1 (Vintage Fair): Willow, Copper
    # Market 2 (Farmers): Sweet, Urban - Market 3 (Craft): Copper, Urban
    # Market 4 (Flea): all
    market_vendor_assignments = [
        [0, 1, 2, 3],           # Sunday Artisan - all vendors
        [0, 1],                 # Vintage Fair - vintage/clothing, jewelry
        [2, 3],                 # Farmers Market - food, home goods
        [1, 2],                 # Craft & Makers - jewelry, home
        [0, 1, 2, 3],           # Flea Market - all
    ]
    for i, mid in enumerate(market_ids):
        for j in market_vendor_assignments[i % len(market_vendor_assignments)]:
            vid = vendor_ids[j]
            is_featured = j < 2
            sb.table("market_vendors").insert({
                "market_id": mid,
                "vendor_id": vid,
                "is_featured_at_market": is_featured,
            }).execute()

    # -------------------------------------------------------------------------
    # Vendor posts - sample posts with captions
    # -------------------------------------------------------------------------
    post_images = [
        "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800",
        "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800",
        "https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=800",
        "https://images.unsplash.com/photo-1578749556568-bc2c40e68b61?w=800",
        "https://images.unsplash.com/photo-1610701596007-11502861dcfa?w=800",
        "https://images.unsplash.com/photo-1591561954557-26941169b49e?w=800",
        "https://images.unsplash.com/photo-1611085583191-a3b181a88401?w=800",
        "https://images.unsplash.com/photo-1566150905458-1bf1fc113f0d?w=800",
    ]
    post_captions = [
        "Fresh batch from the kiln! Coming to Sunday Artisan Market this weekend 🏺",
        "New earring designs dropping at the Vintage Fair. Stop by our booth! ✨",
        "Handcrafted walnut cutting boards - perfect for the home chef 🪵",
        "Sweet treats for your weekend. Find us at the Farmers Market! 🍰",
        "Booth setup for this Saturday - who's coming? 🛍️",
        "Behind the scenes: prepping for Craft & Makers Fair 📦",
        "Vintage finds ready for the Flea Market Extravaganza 🌟",
        "Our bestsellers are back in stock. See you at the market! 💎",
    ]
    post_ids = []
    for i, vid in enumerate(vendor_ids):
        num_posts = 2 if i < 2 else 1
        for p in range(num_posts):
            idx = (i * 2 + p) % len(post_images)
            cap_idx = (i * 2 + p) % len(post_captions)
            r = sb.table("vendor_posts").insert({
                "vendor_id": vid,
                "image_url": post_images[idx],
                "caption": post_captions[cap_idx],
            }).execute()
            if r.data:
                post_ids.append(r.data[0]["id"])

    # -------------------------------------------------------------------------
    # Post comments - use vendor profile_ids as commenters
    # -------------------------------------------------------------------------
    vendors_with_profiles = (
        sb.table("vendors")
        .select("id, profile_id")
        .in_("id", vendor_ids)
        .execute()
    )
    vendor_profile_map = {str(v["id"]): str(v["profile_id"]) for v in (vendors_with_profiles.data or [])}
    sample_comments = [
        "Love this! Can't wait to see it in person 🌟",
        "So beautiful! Where will you be this weekend?",
        "Amazing work as always!",
        "Definitely stopping by your booth!",
        "This looks incredible 😍",
        "Adding to my list for the market visit!",
        "Stunning pieces!",
        "Can't wait to pick one up!",
    ]
    for i, pid in enumerate(post_ids[:6]):
        num_comments = 2 if i < 4 else 1
        for c in range(num_comments):
            commenter_vid = vendor_ids[(i + c) % len(vendor_ids)]
            profile_id = vendor_profile_map.get(str(commenter_vid))
            if not profile_id:
                continue
            comment_text = sample_comments[(i + c) % len(sample_comments)]
            sb.table("post_comments").insert({
                "post_id": pid,
                "profile_id": profile_id,
                "comment_text": comment_text,
            }).execute()

    # -------------------------------------------------------------------------
    # Dev vendor - for auth bypass testing (backend uses this profile_id when auth_enabled=False)
    # -------------------------------------------------------------------------
    DEV_VENDOR_PROFILE_ID = "3dcc239c-78b3-46b3-afef-56e39647fff2"
    dev_email = "dev-vendor@tent.local"
    dev_password = "DevVendor123!"
    try:
        sb.auth.admin.create_user({
            "email": dev_email,
            "password": dev_password,
            "email_confirm": True,
            "id": DEV_VENDOR_PROFILE_ID,
        })
    except Exception as e:
        err_msg = str(e).lower()
        if any(x in err_msg for x in ("already been registered", "already exists", "duplicate", "user")):
            pass  # User exists
        else:
            print(f"Note: Dev vendor auth user may need manual creation: {e}")
    sb.table("profiles").upsert(
        {"id": DEV_VENDOR_PROFILE_ID, "role": "vendor"},
        on_conflict="id",
    ).execute()
    existing_dev = sb.table("vendors").select("id").eq("profile_id", DEV_VENDOR_PROFILE_ID).execute()
    if not existing_dev.data:
        sb.table("vendors").insert({
            "profile_id": DEV_VENDOR_PROFILE_ID,
            "name": "Dev Vendor",
            "slug": "dev-vendor",
            "categories": ["Vintage", "Crafts & DIY"],
            "profile_image_url": "https://images.unsplash.com/photo-1752401984776-edc407a13e1e?w=400",
            "follower_count": 0,
        }).execute()

    print("Seed completed successfully.")


if __name__ == "__main__":
    seed()
