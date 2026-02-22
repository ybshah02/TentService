-- Function to list markets with optional filters (category, date range, min vendors).
-- Used by GET /markets with query params.
--
-- Run this in Supabase SQL Editor (Dashboard → SQL Editor) to enable backend filtering:
--   Copy contents of this file and execute.
CREATE OR REPLACE FUNCTION list_filtered_markets(
  p_limit INT DEFAULT 20,
  p_offset INT DEFAULT 0,
  p_category TEXT DEFAULT NULL,
  p_date_range TEXT DEFAULT NULL,
  p_min_vendors INT DEFAULT NULL
)
RETURNS TABLE (
  total_count BIGINT,
  id UUID,
  admin_id UUID,
  name VARCHAR(255),
  slug VARCHAR(255),
  description TEXT,
  location_name VARCHAR(255),
  location_address TEXT,
  location_city VARCHAR(100),
  location_state VARCHAR(100),
  location_lat DECIMAL,
  location_lng DECIMAL,
  start_date DATE,
  end_date DATE,
  start_time TIME,
  end_time TIME,
  image_url TEXT,
  is_published BOOLEAN,
  interested_count INT,
  vendor_count INT,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
) AS $$
DECLARE
  v_start_date DATE;
  v_end_date DATE;
  v_category_match TEXT;
BEGIN
  -- Resolve date range to actual dates
  IF p_date_range = 'Today' THEN
    v_start_date := CURRENT_DATE;
    v_end_date := CURRENT_DATE;
  ELSIF p_date_range = 'This Week' THEN
    v_start_date := CURRENT_DATE;
    v_end_date := CURRENT_DATE + INTERVAL '7 days';
  ELSIF p_date_range = 'This Month' THEN
    v_start_date := CURRENT_DATE;
    v_end_date := CURRENT_DATE + INTERVAL '1 month';
  ELSIF p_date_range = 'Next Month' THEN
    v_start_date := CURRENT_DATE + INTERVAL '1 month';
    v_end_date := CURRENT_DATE + INTERVAL '2 months';
  ELSE
    -- 'All' or NULL: no date filter
    v_start_date := NULL;
    v_end_date := NULL;
  END IF;

  -- Map filter bar category to vendor categories (for overlap check)
  -- Filter bar: All, Clothing, Jewelry, Food, Art, Vintage, Home
  -- Vendor categories: Clothing, Jewelry, Food & Beverages, Art & Prints, Home Goods, Vintage, etc.
  v_category_match := CASE
    WHEN p_category IS NULL OR p_category = '' OR p_category = 'All' THEN NULL
    WHEN p_category = 'Food' THEN 'Food & Beverages'
    WHEN p_category = 'Art' THEN 'Art & Prints'
    WHEN p_category = 'Home' THEN 'Home Goods'
    ELSE p_category
  END;

  RETURN QUERY
  WITH filtered AS (
    SELECT m.*
    FROM markets m
    WHERE m.is_published = TRUE
      AND (v_start_date IS NULL OR m.end_date >= v_start_date)
      AND (v_end_date IS NULL OR m.start_date <= v_end_date)
      AND (p_min_vendors IS NULL OR m.vendor_count >= p_min_vendors)
      AND (
        v_category_match IS NULL
        OR EXISTS (
          SELECT 1 FROM market_vendors mv
          JOIN vendors v ON v.id = mv.vendor_id
          WHERE mv.market_id = m.id
            AND (v.categories @> ARRAY[v_category_match] OR v_category_match = ANY(v.categories))
        )
      )
  ),
  counted AS (SELECT COUNT(*)::BIGINT AS cnt FROM filtered)
  SELECT
    c.cnt,
    f.id, f.admin_id, f.name, f.slug, f.description,
    f.location_name, f.location_address, f.location_city, f.location_state,
    f.location_lat, f.location_lng, f.start_date, f.end_date,
    f.start_time, f.end_time, f.image_url, f.is_published,
    f.interested_count, f.vendor_count, f.created_at, f.updated_at
  FROM (SELECT * FROM filtered ORDER BY start_date ASC LIMIT p_limit OFFSET p_offset) f
  CROSS JOIN counted c;
END;
$$ LANGUAGE plpgsql STABLE;
