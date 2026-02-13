-- Gen360 Database Setup Script
-- Set password for linuxuser
ALTER USER linuxuser WITH PASSWORD 'r!(hFarm96g5Ayb3INF6';

-- Grant all privileges on database
GRANT ALL PRIVILEGES ON DATABASE normas TO linuxuser;

-- Change database owner
ALTER DATABASE normas OWNER TO linuxuser;

-- Verify user
\du linuxuser

-- Connect to normas database
\c normas

-- List current tables
\dt
