"""Vendor schemas - API response models."""

from uuid import UUID

from pydantic import BaseModel


class VendorResponse(BaseModel):
    """Schema for vendor in API responses."""

    id: UUID
    profile_id: UUID
    name: str
    slug: str
    description: str | None
    categories: list[str]
    profile_image_url: str | None
    gallery_images: list[str]
    instagram_handle: str | None
    depop_handle: str | None
    tiktok_handle: str | None
    website_url: str | None
    is_featured_global: bool
    follower_count: int
    interested_count: int
    created_at: str
    updated_at: str


class MarketVendorResponse(BaseModel):
    """Vendor as returned in market vendors list - includes market-specific fields."""

    id: UUID
    name: str
    slug: str
    categories: list[str]
    profile_image_url: str | None
    follower_count: int
    is_featured_at_market: bool
