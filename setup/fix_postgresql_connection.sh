#!/bin/bash
# Script to configure PostgreSQL for remote connections from Azure

echo "=== Configuring PostgreSQL for Remote Connections ==="

# 1. Check if PostgreSQL is running
echo "Checking PostgreSQL status..."
sudo systemctl status postgresql | head -5

# 2. Find PostgreSQL version and data directory
PG_VERSION=$(psql --version | grep -oP '\d+' | head -1)
echo "PostgreSQL version: $PG_VERSION"

# 3. Configure postgresql.conf to listen on all addresses
echo "Configuring postgresql.conf..."
sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" /etc/postgresql/*/main/postgresql.conf
sudo sed -i "s/listen_addresses = 'localhost'/listen_addresses = '*'/" /etc/postgresql/*/main/postgresql.conf

# 4. Configure pg_hba.conf to accept connections
echo "Configuring pg_hba.conf..."
sudo bash -c 'echo "# Azure Web App connection" >> /etc/postgresql/*/main/pg_hba.conf'
sudo bash -c 'echo "host    normas    linuxuser    0.0.0.0/0    md5" >> /etc/postgresql/*/main/pg_hba.conf'
sudo bash -c 'echo "host    all       linuxuser    0.0.0.0/0    md5" >> /etc/postgresql/*/main/pg_hba.conf'

# 5. Configure firewall to allow PostgreSQL port
echo "Configuring firewall..."
sudo ufw allow 5432/tcp
sudo ufw status

# 6. Restart PostgreSQL
echo "Restarting PostgreSQL..."
sudo systemctl restart postgresql
sudo systemctl status postgresql | head -5

# 7. Test if PostgreSQL is listening
echo "Checking if PostgreSQL is listening on port 5432..."
sudo netstat -plnt | grep 5432

# 8. Create or verify the database and schema
echo "Setting up database schema..."
sudo -u postgres psql -c "SELECT version();"
sudo -u postgres psql -d normas -c "\dt" || echo "Need to create tables"

echo ""
echo "=== Configuration Complete ==="
echo "To create the database schema, run:"
echo "  sudo -u postgres psql -d normas -f /path/to/models.sql"
