-- Migration: Add age and gender to profiles (recommendation-only, not shown on profiles)
-- Run this if you have an existing database from v1 schema

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS age INTEGER;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS gender VARCHAR(100);
