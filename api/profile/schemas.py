"""Profile stats schemas."""

from pydantic import BaseModel


class ProfileStatsResponse(BaseModel):
    """Profile stats for display on profile screen."""

    markets_attended: int  # Vendors: markets joined. Customers: markets interested in.
    followers_or_following: int  # Vendors: customers following. Customers: vendors following.
    interested: int  # Vendors: people interested in vendor. Customers: posts liked.
