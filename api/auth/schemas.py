"""Auth API schemas."""
from pydantic import BaseModel, Field

MAX_GALLERY_PHOTOS = 5


class OnboardCustomerRequest(BaseModel):
    """Onboarding payload for customer."""

    name: str = Field(..., min_length=1, max_length=255)
    location_city: str | None = None
    location_state: str | None = None
    location_lat: float | None = None
    location_lng: float | None = None
    allow_location: bool = False
    age: int | None = None
    gender: str | None = None
    interests: list[str] = Field(default_factory=list, max_length=20)


class OnboardVendorRequest(BaseModel):
    """Onboarding payload for vendor."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    categories: list[str] = Field(default_factory=list, max_length=20)
    age: int | None = None
    gender: str | None = None
    profile_image_url: str | None = None
    gallery_images: list[str] = Field(default_factory=list, max_length=MAX_GALLERY_PHOTOS)
    instagram_handle: str | None = None
    depop_handle: str | None = None
    tiktok_handle: str | None = None
    website_url: str | None = None

