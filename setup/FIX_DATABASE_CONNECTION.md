# ====================================================================

# PostgreSQL Connection Fix Guide for Azure Web App

# ====================================================================

## Current Issue

The Azure Web App at `app-gen360-api.azurewebsites.net` cannot connect
to PostgreSQL server at `20.226.39.175:5432`.

Error: "Connection refused - Is the server running and accepting TCP/IP connections?"

## Root Causes

1. PostgreSQL not configured to accept remote connections
2. PostgreSQL firewall (pg_hba.conf) blocking external IPs
3. VM firewall/NSG blocking port 5432
4. PostgreSQL not listening on external interface

---

## Solution Steps

### Step 1: Connect to PostgreSQL VM

```bash
# SSH into your VM
ssh linuxuser@20.226.39.175
```

### Step 2: Run Configuration Script

Upload and run `fix_postgresql_connection.sh`:

```bash
# On your local machine
scp setup/fix_postgresql_connection.sh linuxuser@20.226.39.175:~/

# On the VM
chmod +x fix_postgresql_connection.sh
./fix_postgresql_connection.sh
```

### Step 3: Initialize Database Schema

```bash
# Upload the schema file
scp db/models.sql linuxuser@20.226.39.175:~/

# On the VM, run:
sudo -u postgres psql -d normas -f ~/models.sql
```

### Step 4: Verify Database Tables

```bash
sudo -u postgres psql -d normas -c "\dt"
sudo -u postgres psql -d normas -c "SELECT COUNT(*) FROM admins;"
```

### Step 5: Configure Azure NSG (Network Security Group)

Check if the VM's NSG allows port 5432:

```powershell
# Run on your local machine
az vm list --resource-group DemoGoverno --output table

# Get the VM network details
az vm show --name <VM-NAME> --resource-group DemoGoverno --query networkProfile

# List NSG rules
az network nsg list --resource-group DemoGoverno --output table
az network nsg rule list --nsg-name <NSG-NAME> --resource-group DemoGoverno --output table

# Add rule to allow PostgreSQL (if needed)
az network nsg rule create `
    --resource-group DemoGoverno `
    --nsg-name <NSG-NAME> `
    --name AllowPostgreSQL `
    --protocol tcp `
    --priority 1000 `
    --destination-port-range 5432 `
    --access allow `
    --direction inbound
```

### Step 6: Verify Connection from Azure

```bash
# Test the connection
curl https://app-gen360-api.azurewebsites.net/health/db
```

Expected result:

```json
{
  "status": "ok",
  "database_connected": true,
  "tables": {
    "admins_exists": true,
    "norma_exists": true,
    "admin_count": 0
  }
}
```

---

## Alternative: Use Azure Database for PostgreSQL

Instead of managing a VM, consider Azure Database for PostgreSQL:

### Benefits:

- Automatic backups
- High availability
- Automatic updates
- Built-in firewall
- Better security

### Quick Setup:

```powershell
# Create Azure PostgreSQL Flexible Server
az postgres flexible-server create `
    --resource-group DemoGoverno `
    --name pg-gen360 `
    --location brazilsouth `
    --admin-user adminuser `
    --admin-password 'SecurePassword123!' `
    --sku-name Standard_B1ms `
    --tier Burstable `
    --version 14 `
    --storage-size 32 `
    --public-access 0.0.0.0

# Create database
az postgres flexible-server db create `
    --resource-group DemoGoverno `
    --server-name pg-gen360 `
    --database-name normas

# Allow Azure services
az postgres flexible-server firewall-rule create `
    --resource-group DemoGoverno `
    --name pg-gen360 `
    --rule-name AllowAzureServices `
    --start-ip-address 0.0.0.0 `
    --end-ip-address 0.0.0.0

# Update Web App settings
az webapp config appsettings set `
    --name app-gen360-api `
    --resource-group DemoGoverno `
    --settings `
        DB_HOST="pg-gen360.postgres.database.azure.com" `
        DB_USER="adminuser" `
        DB_PASSWORD="SecurePassword123!" `
        DB_NAME="normas"
```

---

## Troubleshooting

### Check if PostgreSQL is running on VM

```bash
sudo systemctl status postgresql
sudo netstat -plnt | grep 5432
```

### Check PostgreSQL logs

```bash
sudo tail -f /var/log/postgresql/postgresql-*-main.log
```

### Test local connection on VM

```bash
psql -h 127.0.0.1 -U linuxuser -d normas
```

### Test remote connection from Azure

```bash
# On Azure Web App console (Advanced Tools -> SSH)
apt-get update && apt-get install -y postgresql-client
psql -h 20.226.39.175 -U linuxuser -d normas
```

---

## Security Recommendations

1. **Restrict IP addresses**: Instead of 0.0.0.0/0, use specific Azure Web App IPs:

   ```powershell
   # Get Web App outbound IPs
   az webapp show --name app-gen360-api --resource-group DemoGoverno --query outboundIpAddresses
   ```

2. **Use SSL/TLS**: Configure PostgreSQL to require SSL connections

3. **Use Azure Private Link**: For production, use Private Link instead of public IPs

4. **Rotate credentials**: Change default passwords regularly

---

## Next Steps After Fix

Once the database connection is working:

1. Test the registration endpoint:

   ```bash
   curl -X POST https://app-gen360-api.azurewebsites.net/admin/register \
     -H "Content-Type: application/json" \
     -d '{"email": "admin@example.com", "senha": "Test123!@#"}'
   ```

2. Verify the database health:

   ```bash
   curl https://app-gen360-api.azurewebsites.net/health/db
   ```

3. Create your first admin user through the registration flow
