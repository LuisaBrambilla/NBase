# Check Database Connection Status and Get Azure Web App Info
# Run this script to diagnose the database connection issue

Write-Host "=== Gen360 Database Connection Diagnostic ===" -ForegroundColor Cyan
Write-Host ""

# 1. Check Azure Web App Status
Write-Host "[1/5] Checking Azure Web App status..." -ForegroundColor Yellow
$webappStatus = az webapp show --name app-gen360-api --resource-group DemoGoverno --query "state" -o tsv
Write-Host "Web App State: $webappStatus" -ForegroundColor Green
Write-Host ""

# 2. Get Web App Outbound IP Addresses
Write-Host "[2/5] Getting Web App outbound IP addresses..." -ForegroundColor Yellow
$outboundIPs = az webapp show --name app-gen360-api --resource-group DemoGoverno --query "outboundIpAddresses" -o tsv
$possibleOutboundIPs = az webapp show --name app-gen360-api --resource-group DemoGoverno --query "possibleOutboundIpAddresses" -o tsv

Write-Host "Current Outbound IPs:" -ForegroundColor Green
$outboundIPs -split ',' | ForEach-Object { Write-Host "  - $_" }
Write-Host ""
Write-Host "All Possible Outbound IPs (for firewall whitelist):" -ForegroundColor Green
$possibleOutboundIPs -split ',' | ForEach-Object { Write-Host "  - $_" }
Write-Host ""

# 3. Check Current Database Configuration
Write-Host "[3/5] Checking current database configuration..." -ForegroundColor Yellow
$dbHost = az webapp config appsettings list --name app-gen360-api --resource-group DemoGoverno --query "[?name=='DB_HOST'].value" -o tsv
$dbPort = az webapp config appsettings list --name app-gen360-api --resource-group DemoGoverno --query "[?name=='DB_PORT'].value" -o tsv
$dbName = az webapp config appsettings list --name app-gen360-api --resource-group DemoGoverno --query "[?name=='DB_NAME'].value" -o tsv
$dbUser = az webapp config appsettings list --name app-gen360-api --resource-group DemoGoverno --query "[?name=='DB_USER'].value" -o tsv

Write-Host "Database Configuration:" -ForegroundColor Green
Write-Host "  Host: $dbHost"
Write-Host "  Port: $dbPort"
Write-Host "  Database: $dbName"
Write-Host "  User: $dbUser"
Write-Host ""

# 4. Test Database Health Endpoint
Write-Host "[4/5] Testing database health endpoint..." -ForegroundColor Yellow
try {
    $healthResponse = Invoke-RestMethod -Uri "https://app-gen360-api.azurewebsites.net/health/db" -Method Get
    
    if ($healthResponse.status -eq "ok") {
        Write-Host "✅ Database connection: SUCCESS" -ForegroundColor Green
        Write-Host "Tables status:" -ForegroundColor Green
        Write-Host "  - admins table exists: $($healthResponse.tables.admins_exists)"
        Write-Host "  - norma table exists: $($healthResponse.tables.norma_exists)"
        Write-Host "  - Admin count: $($healthResponse.tables.admin_count)"
    }
    else {
        Write-Host "❌ Database connection: FAILED" -ForegroundColor Red
        Write-Host "Error: $($healthResponse.error)" -ForegroundColor Red
        Write-Host ""
        Write-Host "Traceback:" -ForegroundColor Yellow
        Write-Host $healthResponse.traceback
    }
}
catch {
    Write-Host "❌ Failed to reach health endpoint: $_" -ForegroundColor Red
}
Write-Host ""

# 5. Test Application Endpoint
Write-Host "[5/5] Testing application health..." -ForegroundColor Yellow
try {
    $appHealth = Invoke-RestMethod -Uri "https://app-gen360-api.azurewebsites.net/health" -Method Get
    Write-Host "✅ Application: $($appHealth.status)" -ForegroundColor Green
}
catch {
    Write-Host "❌ Application not responding: $_" -ForegroundColor Red
}
Write-Host ""

# Summary and Next Steps
Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "To fix the database connection issue:" -ForegroundColor Yellow
Write-Host "1. SSH into PostgreSQL VM: ssh linuxuser@$dbHost"
Write-Host "2. Run the fix script: ./setup/fix_postgresql_connection.sh"
Write-Host "3. Whitelist these IPs in PostgreSQL VM firewall/NSG:"
$possibleOutboundIPs -split ',' | ForEach-Object { Write-Host "   $_" }
Write-Host ""
Write-Host "For detailed instructions, see: setup/FIX_DATABASE_CONNECTION.md" -ForegroundColor Green
Write-Host ""

# Create pg_hba.conf entries
Write-Host "=== PostgreSQL pg_hba.conf entries ===" -ForegroundColor Cyan
Write-Host "Add these lines to /etc/postgresql/*/main/pg_hba.conf:" -ForegroundColor Yellow
Write-Host ""
Write-Host "# Azure Web App connections"
$possibleOutboundIPs -split ',' | ForEach-Object { 
    $ip = $_.Trim()
    Write-Host "host    normas    linuxuser    $ip/32    md5"
}
Write-Host "# Or allow all (less secure):"
Write-Host "host    normas    linuxuser    0.0.0.0/0    md5"
Write-Host ""
