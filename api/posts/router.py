"""Posts API - list, create, comments."""

from fastapi import APIRouter, Depends, HTTPException, Query

from api.auth.dependencies import AuthUser, optional_auth, require_auth
from api.schemas.post import (
    PostCommentCreate,
    PostCommentResponse,
    PostCreate,
    PostListResponse,
    PostResponse,
)
from db.supabase import get_supabase

router = APIRouter(prefix="/posts", tags=["posts"])

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


@router.get("/health")
async def posts_health():
    """Posts module health check."""
    return {"status": "ok", "module": "posts"}


@router.get("", response_model=PostListResponse)
async def list_posts(
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    vendor_id: str | None = Query(default=None, description="Filter by vendor"),
    user: AuthUser | None = Depends(optional_auth),
):
    """List posts (feed) with vendor info. Optionally filter by vendor_id."""
    supabase = get_supabase()

    query = (
        supabase.table("vendor_posts")
        .select(
            "id, vendor_id, image_url, caption, like_count, comment_count, created_at, updated_at",
            count="exact",
        )
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
    )

    if vendor_id:
        query = query.eq("vendor_id", vendor_id)

    response = query.execute()
    items_raw = response.data or []

    # Get liked post ids for current user
    liked_post_ids: set[str] = set()
    if user and items_raw:
        post_ids = [str(r["id"]) for r in items_raw]
        like_resp = (
            supabase.table("interactions")
            .select("post_id")
            .eq("profile_id", user.id)
            .eq("type", "like")
            .in_("post_id", post_ids)
            .execute()
        )
        liked_post_ids = {str(r["post_id"]) for r in (like_resp.data or [])}

    # Enrich with vendor info
    vendor_ids = list({str(r["vendor_id"]) for r in items_raw})
    vendors_map = {}
    if vendor_ids:
        vendors_resp = (
            supabase.table("vendors")
            .select("id, name, slug, profile_image_url")
            .in_("id", vendor_ids)
            .execute()
        )
        for v in vendors_resp.data or []:
            vendors_map[str(v["id"])] = v

    items = []
    for row in items_raw:
        vid = str(row["vendor_id"])
        pid = str(row["id"])
        vendor = vendors_map.get(vid)
        items.append(
            PostResponse(
                id=row["id"],
                vendor_id=row["vendor_id"],
                image_url=row["image_url"],
                caption=row.get("caption"),
                like_count=row.get("like_count") or 0,
                comment_count=row.get("comment_count") or 0,
                liked=pid in liked_post_ids,
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
                vendor=(
                    {
                        "id": vendor["id"],
                        "name": vendor["name"],
                        "slug": vendor["slug"],
                        "profile_image_url": vendor.get("profile_image_url"),
                    }
                    if vendor
                    else None
                ),
            )
        )

    total = response.count if response.count is not None else len(items)
    return PostListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{post_id}/like-status")
async def get_post_like_status(
    post_id: str,
    user: AuthUser | None = Depends(optional_auth),
):
    """Get whether the current user has liked this post. Returns liked: false when not authenticated."""
    supabase = get_supabase()

    post_resp = supabase.table("vendor_posts").select("id").eq("id", post_id).execute()
    if not post_resp.data:
        raise HTTPException(status_code=404, detail="Post not found")

    if user is None:
        return {"liked": False}

    resp = (
        supabase.table("interactions")
        .select("id")
        .eq("profile_id", user.id)
        .eq("post_id", post_id)
        .eq("type", "like")
        .execute()
    )
    return {"liked": bool(resp.data and len(resp.data) > 0)}


@router.post("/{post_id}/like", status_code=201)
async def add_post_like(
    post_id: str,
    user: AuthUser = Depends(require_auth),
):
    """Like a post. Requires authentication."""
    supabase = get_supabase()

    post_resp = supabase.table("vendor_posts").select("id").eq("id", post_id).execute()
    if not post_resp.data:
        raise HTTPException(status_code=404, detail="Post not found")

    try:
        supabase.table("interactions").insert({
            "profile_id": user.id,
            "post_id": post_id,
            "type": "like",
        }).execute()
    except Exception as e:
        err = str(e).lower()
        if "duplicate" in err or "unique" in err or "already exists" in err:
            return {"ok": True, "message": "Already liked"}
        raise HTTPException(status_code=500, detail="Failed to like post") from e

    return {"ok": True, "message": "Post liked"}


@router.delete("/{post_id}/like", status_code=200)
async def remove_post_like(
    post_id: str,
    user: AuthUser = Depends(require_auth),
):
    """Remove like from a post. Requires authentication."""
    supabase = get_supabase()

    (
        supabase.table("interactions")
        .delete()
        .eq("profile_id", user.id)
        .eq("post_id", post_id)
        .eq("type", "like")
        .execute()
    )

    return {"ok": True, "message": "Like removed"}


@router.get("/{post_id}/comments", response_model=list[PostCommentResponse])
async def list_post_comments(post_id: str):
    """List comments for a post."""
    supabase = get_supabase()

    # Verify post exists
    post_resp = supabase.table("vendor_posts").select("id").eq("id", post_id).execute()
    if not post_resp.data:
        raise HTTPException(status_code=404, detail="Post not found")

    response = (
        supabase.table("post_comments")
        .select("id, post_id, profile_id, comment_text, created_at, updated_at")
        .eq("post_id", post_id)
        .order("created_at", desc=False)
        .execute()
    )
    rows = response.data or []

    # Resolve author names from profiles -> customers/vendors/admins
    profile_ids = list({str(r["profile_id"]) for r in rows})
    authors_map = {}
    if profile_ids:
        customers = (
            supabase.table("customers").select("profile_id, name").in_("profile_id", profile_ids).execute()
        )
        vendors = (
            supabase.table("vendors").select("profile_id, name").in_("profile_id", profile_ids).execute()
        )
        admins = (
            supabase.table("admins").select("profile_id, name").in_("profile_id", profile_ids).execute()
        )
        for c in (customers.data or []):
            authors_map[str(c["profile_id"])] = c["name"]
        for v in (vendors.data or []):
            authors_map[str(v["profile_id"])] = v["name"]
        for a in (admins.data or []):
            authors_map[str(a["profile_id"])] = a["name"]

    return [
        PostCommentResponse(
            id=r["id"],
            post_id=r["post_id"],
            profile_id=r["profile_id"],
            comment_text=r["comment_text"],
            created_at=str(r["created_at"]),
            updated_at=str(r["updated_at"]),
            author_name=authors_map.get(str(r["profile_id"]), "Anonymous"),
        )
        for r in rows
    ]


@router.post("/{post_id}/comments", response_model=PostCommentResponse, status_code=201)
async def create_post_comment(
    post_id: str,
    body: PostCommentCreate,
    user: AuthUser = Depends(require_auth),
):
    """Add a comment to a post. Requires authentication."""
    supabase = get_supabase()

    post_resp = supabase.table("vendor_posts").select("id").eq("id", post_id).execute()
    if not post_resp.data:
        raise HTTPException(status_code=404, detail="Post not found")

    payload = {
        "post_id": post_id,
        "profile_id": user.id,
        "comment_text": body.comment_text,
    }
    response = supabase.table("post_comments").insert(payload).execute()

    if not response.data or len(response.data) == 0:
        raise HTTPException(status_code=500, detail="Failed to create comment")

    row = response.data[0]

    # Resolve author name
    author_name = "Anonymous"
    for table, key in [("customers", "profile_id"), ("vendors", "profile_id"), ("admins", "profile_id")]:
        r = supabase.table(table).select("name").eq(key, user.id).execute()
        if r.data:
            author_name = r.data[0]["name"]
            break

    return PostCommentResponse(
        id=row["id"],
        post_id=row["post_id"],
        profile_id=row["profile_id"],
        comment_text=row["comment_text"],
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        author_name=author_name,
    )


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: str,
    user: AuthUser | None = Depends(optional_auth),
):
    """Get a single post by ID with vendor info."""
    supabase = get_supabase()

    response = (
        supabase.table("vendor_posts")
        .select("*")
        .eq("id", post_id)
        .execute()
    )
    if not response.data or len(response.data) == 0:
        raise HTTPException(status_code=404, detail="Post not found")

    row = response.data[0]
    vendor_id = str(row["vendor_id"])
    vendor_resp = (
        supabase.table("vendors")
        .select("id, name, slug, profile_image_url")
        .eq("id", vendor_id)
        .execute()
    )
    vendor = vendor_resp.data[0] if vendor_resp.data else None

    liked = False
    if user:
        like_resp = (
            supabase.table("interactions")
            .select("id")
            .eq("profile_id", user.id)
            .eq("post_id", post_id)
            .eq("type", "like")
            .execute()
        )
        liked = bool(like_resp.data and len(like_resp.data) > 0)

    return PostResponse(
        id=row["id"],
        vendor_id=row["vendor_id"],
        image_url=row["image_url"],
        caption=row.get("caption"),
        like_count=row.get("like_count") or 0,
        comment_count=row.get("comment_count") or 0,
        liked=liked,
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        vendor=(
            {
                "id": vendor["id"],
                "name": vendor["name"],
                "slug": vendor["slug"],
                "profile_image_url": vendor.get("profile_image_url"),
            }
            if vendor
            else None
        ),
    )


@router.post("", response_model=PostResponse, status_code=201)
async def create_post(
    body: PostCreate,
    user: AuthUser = Depends(require_auth),
):
    """Create a new post. Requires vendor authentication."""
    supabase = get_supabase()

    # Resolve vendor for this profile
    vendor_resp = (
        supabase.table("vendors")
        .select("id")
        .eq("profile_id", user.id)
        .execute()
    )
    if not vendor_resp.data:
        raise HTTPException(
            status_code=403,
            detail="Only vendors can create posts. Complete vendor onboarding first.",
        )
    vendor_id = vendor_resp.data[0]["id"]

    payload = {
        "vendor_id": str(vendor_id),
        "image_url": body.image_url,
        "caption": body.caption or None,
    }
    response = supabase.table("vendor_posts").insert(payload).execute()

    if not response.data or len(response.data) == 0:
        raise HTTPException(status_code=500, detail="Failed to create post")

    row = response.data[0]
    v_resp = (
        supabase.table("vendors")
        .select("id, name, slug, profile_image_url")
        .eq("id", vendor_id)
        .execute()
    )
    v = v_resp.data[0] if v_resp.data else {"id": vendor_id, "name": "Vendor", "slug": "", "profile_image_url": None}

    return PostResponse(
        id=row["id"],
        vendor_id=row["vendor_id"],
        image_url=row["image_url"],
        caption=row.get("caption"),
        like_count=row.get("like_count") or 0,
        comment_count=row.get("comment_count") or 0,
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        vendor={
            "id": v["id"],
            "name": v["name"],
            "slug": v["slug"],
            "profile_image_url": v.get("profile_image_url"),
        },
    )
