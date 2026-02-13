-- =============================================================
-- Fix PostgreSQL permissions for the Gen360 application user
-- Run these statements as a superuser (e.g., postgres)
-- psql -U postgres -d normas -f setup/fix_db_permissions.sql
-- =============================================================

-- Ensure linuxuser can access all tables in public schema
GRANT USAGE ON SCHEMA public TO linuxuser;

-- Grant DML permissions on critical tables
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO linuxuser;

-- Grant privileges on future tables automatically
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO linuxuser;

-- Grant sequence usage (needed for UUID defaults, serials, etc.)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO linuxuser;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES TO linuxuser;

-- Optional: verify
-- \z admins
-- SELECT grantee, privilege_type FROM information_schema.table_privileges WHERE table_name = 'admins';
