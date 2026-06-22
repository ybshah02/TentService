"""Dashboard API - metrics for TentDashboard app."""

from datetime import date

from fastapi import APIRouter

from db.supabase import get_supabase

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats():
    """
    Return aggregate metrics for the dashboard: onboarded counts,
    posting activity, likes/comments, and today's signups/logins.
    """
    supabase = get_supabase()

    try:
        r = supabase.rpc("get_dashboard_stats").execute()
        if r.data is not None and len(r.data) > 0:
            raw = r.data[0]
            if isinstance(raw, dict):
                if "get_dashboard_stats" in raw:
                    return raw["get_dashboard_stats"]
                return raw
            return {"data": raw}
    except Exception:
        pass

    # Fallback: compute stats without the DB function (no auth.users, no distinct counts)
    today = date.today().isoformat()

    def _count(table: str, extra_filters=None):
        q = supabase.table(table).select("*", count="exact").limit(1)
        if extra_filters:
            for key, value in extra_filters.items():
                q = q.eq(key, value)
        resp = q.execute()
        return getattr(resp, "count", None) or len(resp.data or [])

    vendors_total = _count("vendors")
    markets_total = _count("markets")
    customers_total = _count("customers")
    posts_total = _count("vendor_posts")
    comments_total = _count("post_comments")

    # Likes: interactions with type=like and post_id set
    like_resp = (
        supabase.table("interactions")
        .select("id", count="exact")
        .eq("type", "like")
        .not_.is_("post_id", "null")
        .limit(1)
        .execute()
    )
    likes_total = getattr(like_resp, "count", None) or len(like_resp.data or [])

    # Vendors who have posted (distinct vendor_id from vendor_posts)
    vp_resp = supabase.table("vendor_posts").select("vendor_id").execute()
    vendor_ids = [r["vendor_id"] for r in (vp_resp.data or []) if r.get("vendor_id")]
    vendors_with_posts = len(set(vendor_ids))

    # Markets that have at least one vendor who has posted
    if not vendor_ids:
        markets_with_posting_vendors = 0
    else:
        mv_resp = (
            supabase.table("market_vendors")
            .select("market_id")
            .in_("vendor_id", vendor_ids[:100])
            .execute()
        )
        markets_with_posting_vendors = len(set(r["market_id"] for r in (mv_resp.data or []) if r.get("market_id")))

    # Profiles created today (profiles table has created_at)
    profiles_resp = (
        supabase.table("profiles")
        .select("id", count="exact")
        .gte("created_at", f"{today}T00:00:00")
        .limit(1)
        .execute()
    )
    profiles_created_today = getattr(profiles_resp, "count", None) or len(profiles_resp.data or [])

    return {
        "vendors_total": vendors_total,
        "markets_total": markets_total,
        "customers_total": customers_total,
        "vendors_with_posts": vendors_with_posts,
        "markets_with_posting_vendors": markets_with_posting_vendors,
        "posts_total": posts_total,
        "likes_total": likes_total,
        "comments_total": comments_total,
        "profiles_created_today": profiles_created_today,
        "logins_today": None,
    }
