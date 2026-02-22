-- Pre-launch vendor signup aggregation.
-- Stores vendor interest data (email, name, markets) before they create accounts.
-- When they sign up later, match by email and send forgot-password link.

CREATE TABLE IF NOT EXISTS vendor_signups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    categories TEXT[] DEFAULT '{}',
    profile_image_url TEXT,
    gallery_images TEXT[] DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS vendor_signup_markets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor_signup_id UUID NOT NULL REFERENCES vendor_signups(id) ON DELETE CASCADE,
    market_id UUID NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(vendor_signup_id, market_id)
);

CREATE INDEX idx_vendor_signup_markets_signup ON vendor_signup_markets(vendor_signup_id);
CREATE INDEX idx_vendor_signup_markets_market ON vendor_signup_markets(market_id);
