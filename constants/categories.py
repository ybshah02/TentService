"""Category constants - single source of truth for filters and vendor categories."""

# Display label for "All" in filter bar
FILTER_CATEGORY_ALL = "All"

# Categories shown in filter bar (horizontal scroll)
FILTER_CATEGORIES = [
    FILTER_CATEGORY_ALL,
    "Clothing",
    "Jewelry",
    "Food",
    "Art",
    "Vintage",
    "Home",
]

# Full list for filter modal (matches vendor categories in DB)
VENDOR_CATEGORIES = [
    "Clothing",
    "Jewelry",
    "Food & Beverages",
    "Art & Prints",
    "Home Goods",
    "Vintage",
    "Crafts & DIY",
    "Books & Media",
]

# Date range options for filter modal
DATE_RANGES = [
    "Today",
    "This Week",
    "This Month",
    "Next Month",
    "All",
]
