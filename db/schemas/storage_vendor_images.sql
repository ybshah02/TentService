-- =============================================================================
-- Supabase Storage: vendor-images bucket setup
-- =============================================================================
--
-- ARCHITECTURE: Frontend → Supabase direct upload (no backend proxy).
-- This is safe and standard: the user's JWT authenticates the request, and
-- RLS policies below restrict uploads to their own folder only.
--
-- SETUP:
-- 1. Supabase Dashboard → Storage → New bucket
--    - Name: vendor-images
--    - Public: Yes (profile images need public URLs)
--    - Optional: File size limit 5MB, Allowed MIME types: image/*
--
-- 2. Run this SQL in Supabase SQL Editor to add RLS policies.
-- =============================================================================

-- Allow authenticated users to upload only to their own folder (vendor-images/{user_id}/*)
CREATE POLICY "Vendor images: users can upload to own folder"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'vendor-images'
  AND (storage.foldername(name))[1] = (auth.jwt()->>'sub')
);

-- Public read access (bucket is public - this allows SELECT for public URLs)
CREATE POLICY "Vendor images: public read access"
ON storage.objects
FOR SELECT
TO public
USING (bucket_id = 'vendor-images');
