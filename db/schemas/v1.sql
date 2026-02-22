-- TENT MARKETPLACE DATABASE SCHEMA
-- PostgreSQL / Supabase syntax
-- Assumes Supabase auth.users table exists for authentication

-- ============================================================================
-- CORE USER MANAGEMENT
-- ============================================================================

-- Business-specific profile data (references Supabase auth.users)
CREATE TABLE profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('customer', 'vendor', 'admin')),
    -- Recommendation-only (not shown on profiles)
    age INTEGER,
    gender VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_profiles_role ON profiles(role);

-- ============================================================================
-- CUSTOMER PROFILES
-- ============================================================================

CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID UNIQUE NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    location_lat DECIMAL(10, 8),
    location_lng DECIMAL(11, 8),
    location_city VARCHAR(100),
    location_state VARCHAR(100),
    allow_location BOOLEAN DEFAULT FALSE,
    
    -- Shopping preferences (array of category strings)
    interests TEXT[] DEFAULT '{}',
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_customers_profile ON customers(profile_id);
CREATE INDEX idx_customers_location ON customers(location_lat, location_lng);

-- ============================================================================
-- VENDOR PROFILES
-- ============================================================================

CREATE TABLE vendors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID UNIQUE NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL, -- for URLs like /vendor/palaks-place
    description TEXT,
    
    -- Categories (array of category strings)
    categories TEXT[] DEFAULT '{}',
    
    profile_image_url TEXT,
    gallery_images TEXT[] DEFAULT '{}', -- Array of image URLs
    
    -- Social links
    instagram_handle VARCHAR(100),
    depop_handle VARCHAR(100),
    tiktok_handle VARCHAR(100),
    website_url TEXT,
    
    -- Premium features
    is_featured_global BOOLEAN DEFAULT FALSE,
    featured_global_expires_at TIMESTAMP,
    
    -- Stats (updated via triggers)
    follower_count INTEGER DEFAULT 0,
    interested_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_vendors_profile ON vendors(profile_id);
CREATE INDEX idx_vendors_slug ON vendors(slug);
CREATE INDEX idx_vendors_featured ON vendors(is_featured_global);

-- ============================================================================
-- ADMIN PROFILES
-- ============================================================================

CREATE TABLE admins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID UNIQUE NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_admins_profile ON admins(profile_id);

-- ============================================================================
-- MARKETS/MARKETPLACES
-- ============================================================================

CREATE TABLE markets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id UUID NOT NULL REFERENCES admins(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    
    -- Location
    location_name VARCHAR(255) NOT NULL, -- "West Mall, UT Austin"
    location_address TEXT,
    location_city VARCHAR(100),
    location_state VARCHAR(100),
    location_lat DECIMAL(10, 8),
    location_lng DECIMAL(11, 8),
    
    -- Dates
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    start_time TIME,
    end_time TIME,
    
    image_url TEXT,
    
    -- Settings
    is_published BOOLEAN DEFAULT FALSE,
    
    -- Stats (updated via triggers)
    interested_count INTEGER DEFAULT 0,
    vendor_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_markets_admin ON markets(admin_id);
CREATE INDEX idx_markets_dates ON markets(start_date, end_date);
CREATE INDEX idx_markets_location ON markets(location_lat, location_lng);
CREATE INDEX idx_markets_published ON markets(is_published);
CREATE INDEX idx_markets_slug ON markets(slug);

-- ============================================================================
-- VENDOR <-> MARKET RELATIONSHIPS
-- ============================================================================

CREATE TABLE market_vendors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    market_id UUID NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
    vendor_id UUID NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    
    -- Featured at this specific market
    is_featured_at_market BOOLEAN DEFAULT FALSE,
    featured_at_market_expires_at TIMESTAMP,
    
    -- Stats for this vendor at this market
    interested_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(market_id, vendor_id)
);

CREATE INDEX idx_market_vendors_market ON market_vendors(market_id);
CREATE INDEX idx_market_vendors_vendor ON market_vendors(vendor_id);
CREATE INDEX idx_market_vendors_featured ON market_vendors(is_featured_at_market);

-- ============================================================================
-- VENDOR POSTS/CONTENT
-- ============================================================================

CREATE TABLE vendor_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor_id UUID NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    caption TEXT,
    
    -- Stats (updated via triggers)
    like_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_vendor_posts_vendor ON vendor_posts(vendor_id);
CREATE INDEX idx_vendor_posts_created ON vendor_posts(created_at DESC);

-- ============================================================================
-- USER INTERACTIONS (replaces separate follows/interests/likes tables)
-- ============================================================================

CREATE TABLE interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    
    -- What they're interacting with (only one should be set)
    vendor_id UUID REFERENCES vendors(id) ON DELETE CASCADE,
    market_id UUID REFERENCES markets(id) ON DELETE CASCADE,
    post_id UUID REFERENCES vendor_posts(id) ON DELETE CASCADE,
    
    -- Type of interaction
    type VARCHAR(20) NOT NULL CHECK (type IN ('follow', 'interested', 'like')),
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Ensure a user can only have one interaction of each type per entity
    UNIQUE(profile_id, vendor_id, type),
    UNIQUE(profile_id, market_id, type),
    UNIQUE(profile_id, post_id, type),
    
    -- Ensure at least one entity is set
    CHECK (
        (vendor_id IS NOT NULL AND market_id IS NULL AND post_id IS NULL) OR
        (vendor_id IS NULL AND market_id IS NOT NULL AND post_id IS NULL) OR
        (vendor_id IS NULL AND market_id IS NULL AND post_id IS NOT NULL)
    )
);

CREATE INDEX idx_interactions_profile ON interactions(profile_id);
CREATE INDEX idx_interactions_vendor ON interactions(vendor_id);
CREATE INDEX idx_interactions_market ON interactions(market_id);
CREATE INDEX idx_interactions_post ON interactions(post_id);
CREATE INDEX idx_interactions_type ON interactions(type);

-- Comments on posts
CREATE TABLE post_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES vendor_posts(id) ON DELETE CASCADE,
    profile_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    comment_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_post_comments_post ON post_comments(post_id);
CREATE INDEX idx_post_comments_profile ON post_comments(profile_id);

-- ============================================================================
-- TRIGGERS FOR COUNTER UPDATES
-- ============================================================================

-- Update vendor follower_count
CREATE OR REPLACE FUNCTION update_vendor_follower_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.type = 'follow' AND NEW.vendor_id IS NOT NULL THEN
        UPDATE vendors SET follower_count = follower_count + 1 WHERE id = NEW.vendor_id;
    ELSIF TG_OP = 'DELETE' AND OLD.type = 'follow' AND OLD.vendor_id IS NOT NULL THEN
        UPDATE vendors SET follower_count = follower_count - 1 WHERE id = OLD.vendor_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_vendor_follower_count
AFTER INSERT OR DELETE ON interactions
FOR EACH ROW EXECUTE FUNCTION update_vendor_follower_count();

-- Update vendor interested_count
CREATE OR REPLACE FUNCTION update_vendor_interested_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.type = 'interested' AND NEW.vendor_id IS NOT NULL THEN
        UPDATE vendors SET interested_count = interested_count + 1 WHERE id = NEW.vendor_id;
    ELSIF TG_OP = 'DELETE' AND OLD.type = 'interested' AND OLD.vendor_id IS NOT NULL THEN
        UPDATE vendors SET interested_count = interested_count - 1 WHERE id = OLD.vendor_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_vendor_interested_count
AFTER INSERT OR DELETE ON interactions
FOR EACH ROW EXECUTE FUNCTION update_vendor_interested_count();

-- Update market interested_count
CREATE OR REPLACE FUNCTION update_market_interested_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.type = 'interested' AND NEW.market_id IS NOT NULL THEN
        UPDATE markets SET interested_count = interested_count + 1 WHERE id = NEW.market_id;
    ELSIF TG_OP = 'DELETE' AND OLD.type = 'interested' AND OLD.market_id IS NOT NULL THEN
        UPDATE markets SET interested_count = interested_count - 1 WHERE id = OLD.market_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_market_interested_count
AFTER INSERT OR DELETE ON interactions
FOR EACH ROW EXECUTE FUNCTION update_market_interested_count();

-- Update post like_count
CREATE OR REPLACE FUNCTION update_post_like_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.type = 'like' AND NEW.post_id IS NOT NULL THEN
        UPDATE vendor_posts SET like_count = like_count + 1 WHERE id = NEW.post_id;
    ELSIF TG_OP = 'DELETE' AND OLD.type = 'like' AND OLD.post_id IS NOT NULL THEN
        UPDATE vendor_posts SET like_count = like_count - 1 WHERE id = OLD.post_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_post_like_count
AFTER INSERT OR DELETE ON interactions
FOR EACH ROW EXECUTE FUNCTION update_post_like_count();

-- Update post comment_count
CREATE OR REPLACE FUNCTION update_post_comment_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE vendor_posts SET comment_count = comment_count + 1 WHERE id = NEW.post_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE vendor_posts SET comment_count = comment_count - 1 WHERE id = OLD.post_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_post_comment_count
AFTER INSERT OR DELETE ON post_comments
FOR EACH ROW EXECUTE FUNCTION update_post_comment_count();

-- Update market vendor_count
CREATE OR REPLACE FUNCTION update_market_vendor_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE markets SET vendor_count = vendor_count + 1 WHERE id = NEW.market_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE markets SET vendor_count = vendor_count - 1 WHERE id = OLD.market_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_market_vendor_count
AFTER INSERT OR DELETE ON market_vendors
FOR EACH ROW EXECUTE FUNCTION update_market_vendor_count();

-- ============================================================================
-- USEFUL VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Upcoming markets
CREATE VIEW upcoming_markets AS
SELECT * 
FROM markets
WHERE is_published = TRUE 
  AND end_date >= CURRENT_DATE
ORDER BY start_date ASC;

-- Featured vendors globally
CREATE VIEW featured_vendors_global AS
SELECT v.* 
FROM vendors v
WHERE v.is_featured_global = TRUE 
  AND (v.featured_global_expires_at IS NULL OR v.featured_global_expires_at > NOW())
ORDER BY v.follower_count DESC;

-- Vendor schedule (what markets they'll be at)
CREATE VIEW vendor_market_schedule AS
SELECT 
    v.id as vendor_id,
    v.name as vendor_name,
    v.slug as vendor_slug,
    m.id as market_id,
    m.name as market_name,
    m.start_date,
    m.end_date,
    m.location_name,
    mv.is_featured_at_market
FROM vendors v
JOIN market_vendors mv ON v.id = mv.vendor_id
JOIN markets m ON mv.market_id = m.id
WHERE m.is_published = TRUE
ORDER BY m.start_date ASC;