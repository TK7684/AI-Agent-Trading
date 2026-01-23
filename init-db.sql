-- Initialize PostgreSQL database for Crypto Platform
-- This script runs automatically on first container start

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create indexes for better performance
-- These will be created after tables are migrated

-- Set timezone to UTC
SET timezone = 'UTC';
