-- Create user and grant permissions
CREATE USER linuxuser WITH PASSWORD 'r!(hFarm96g5Ayb3INF6';
GRANT ALL PRIVILEGES ON DATABASE normas TO linuxuser;
ALTER DATABASE normas OWNER TO linuxuser;
