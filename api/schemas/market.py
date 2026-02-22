"""Market schemas - API response and request models."""

from datetime import date, time
from uuid import UUID

from pydantic import BaseModel, Field


class MarketCreate(BaseModel):
    """Schema for creating a market."""

    admin_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    location_name: str = Field(..., min_length=1, max_length=255)
    location_address: str | None = None
    location_city: str | None = Field(None, max_length=100)
    location_state: str | None = Field(None, max_length=100)
    location_lat: float | None = None
    location_lng: float | None = None
    start_date: date
    end_date: date
    start_time: time | None = None
    end_time: time | None = None
    image_url: str | None = None
    is_published: bool = False


class MarketResponse(BaseModel):
    """Schema for market in API responses."""

    id: UUID
    admin_id: UUID
    name: str
    slug: str
    description: str | None
    location_name: str
    location_address: str | None
    location_city: str | None
    location_state: str | None
    location_lat: float | None
    location_lng: float | None
    start_date: date
    end_date: date
    start_time: time | None
    end_time: time | None
    image_url: str | None
    is_published: bool
    interested_count: int
    vendor_count: int
    created_at: str
    updated_at: str


class MarketListResponse(BaseModel):
    """Paginated list of markets."""

    items: list[MarketResponse]
    total: int
    limit: int
    offset: int
