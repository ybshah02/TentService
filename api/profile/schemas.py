"""Profile stats and update schemas."""

from pydantic import BaseModel, Field


class ProfileMeResponse(BaseModel):
    """Editable profile fields for settings."""

    name: str
    role: str
    location_city: str | None = None
    location_state: str | None = None
    location_lat: float | None = None
    location_lng: float | None = None
    allow_location: bool = False


class ProfileUpdateRequest(BaseModel):
    """Update profile payload."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    location_city: str | None = None
    location_state: str | None = None
    location_lat: float | None = None
    location_lng: float | None = None
    allow_location: bool | None = None
    profile_image_url: str | None = None  # Vendor profile image


class ProfileStatsResponse(BaseModel):
    """Profile stats for display on profile screen."""

    name: str | None  # From customers or vendors table
    interests: list[str]  # Customer interests from onboarding
    vendor_id: str | None  # Vendor's ID (for fetching their posts)
    profile_image_url: str | None = None  # Vendor profile image
    markets_attended: int  # Vendors: markets joined. Customers: markets interested in.
    followers_or_following: int  # Vendors: customers following. Customers: vendors following.
    interested: int  # Vendors: people interested in vendor. Customers: posts liked.
