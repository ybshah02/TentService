"""Post schemas - API response and request models."""

from uuid import UUID

from pydantic import BaseModel, Field


class PostVendorInfo(BaseModel):
    """Minimal vendor info included in post responses."""

    id: UUID
    name: str
    slug: str
    profile_image_url: str | None


class PostCreate(BaseModel):
    """Schema for creating a post."""

    image_url: str = Field(..., min_length=1)
    caption: str | None = None


class PostResponse(BaseModel):
    """Schema for post in API responses."""

    id: UUID
    vendor_id: UUID
    image_url: str
    caption: str | None
    like_count: int
    comment_count: int
    liked: bool = False  # True when current user has liked this post
    created_at: str
    updated_at: str
    vendor: PostVendorInfo | None = None


class PostListResponse(BaseModel):
    """Paginated list of posts."""

    items: list[PostResponse]
    total: int
    limit: int
    offset: int


class PostCommentCreate(BaseModel):
    """Schema for creating a comment."""

    comment_text: str = Field(..., min_length=1, max_length=2000)


class PostCommentResponse(BaseModel):
    """Schema for comment in API responses."""

    id: UUID
    post_id: UUID
    profile_id: UUID
    comment_text: str
    created_at: str
    updated_at: str
    author_name: str | None = None
