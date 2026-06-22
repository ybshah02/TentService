-- Dashboard stats: single RPC returns all metrics (avoids N+1 and supports COUNT DISTINCT).
-- Run this in Supabase SQL editor or migrations, then call via supabase.rpc('get_dashboard_stats').

CREATE OR REPLACE FUNCTION get_dashboard_stats()
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  result JSONB;
  vendors_total BIGINT;
  markets_total BIGINT;
  customers_total BIGINT;
  vendors_with_posts BIGINT;
  markets_with_posting_vendors BIGINT;
  posts_total BIGINT;
  likes_total BIGINT;
  comments_total BIGINT;
  profiles_created_today BIGINT;
  logins_today BIGINT;
BEGIN
  SELECT COUNT(*) INTO vendors_total FROM vendors;
  SELECT COUNT(*) INTO markets_total FROM markets;
  SELECT COUNT(*) INTO customers_total FROM customers;
  SELECT COUNT(DISTINCT vendor_id) INTO vendors_with_posts FROM vendor_posts;
  SELECT COUNT(DISTINCT mv.market_id) INTO markets_with_posting_vendors
    FROM market_vendors mv
    INNER JOIN vendor_posts vp ON vp.vendor_id = mv.vendor_id;
  SELECT COUNT(*) INTO posts_total FROM vendor_posts;
  SELECT COUNT(*) INTO likes_total FROM interactions WHERE type = 'like' AND post_id IS NOT NULL;
  SELECT COUNT(*) INTO comments_total FROM post_comments;
  SELECT COUNT(*) INTO profiles_created_today
    FROM profiles
    WHERE created_at >= date_trunc('day', NOW());
  -- auth.users is in auth schema; only available with service role / direct DB
  BEGIN
    SELECT COUNT(*) INTO logins_today
      FROM auth.users
      WHERE last_sign_in_at >= date_trunc('day', NOW());
  EXCEPTION WHEN OTHERS THEN
    logins_today := NULL;
  END;

  result := jsonb_build_object(
    'vendors_total', vendors_total,
    'markets_total', markets_total,
    'customers_total', customers_total,
    'vendors_with_posts', vendors_with_posts,
    'markets_with_posting_vendors', markets_with_posting_vendors,
    'posts_total', posts_total,
    'likes_total', likes_total,
    'comments_total', comments_total,
    'profiles_created_today', profiles_created_today,
    'logins_today', logins_today
  );
  RETURN result;
END;
$$;
