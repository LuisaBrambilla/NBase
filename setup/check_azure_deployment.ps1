# Azure Deployment Health Check Script for Gen360
# This script verifies all deployed resources and configurations

param(
    [string]$ResourceGroup = "DemoGoverno",
    [string]$PostgreSQLVMName = "postgresql-vm",
    [string]$AppServicePlan = "asp-gen360",
    [string]$WebAppName = "app-gen360-api",
    [string]$StorageAccount = "stgen360frontend",
    [string]$DBHost = "20.226.39.175",
    [string]$DBName = "normas",
    [string]$DBUser = "linuxuser"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Gen360 - Azure Deployment Check" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$errors = @()
$warnings = @()

# Function to check resource
function Check-Resource {
    param(
        [string]$Name,
        [scriptblock]$Check,
        [string]$SuccessMessage,
        [string]$FailMessage
    )
    
    Write-Host "Checking: $Name..." -ForegroundColor Yellow -NoNewline
    try {
        $result = & $Check
        if ($result) {
            Write-Host " ✓" -ForegroundColor Green
            if ($SuccessMessage) {
                Write-Host "  $SuccessMessage" -ForegroundColor Gray
            }
            return $true
        }
        else {
            Write-Host " ✗" -ForegroundColor Red
            $script:errors += $FailMessage
            Write-Host "  $FailMessage" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host " ✗" -ForegroundColor Red
        $script:errors += "$FailMessage - Error: $($_.Exception.Message)"
        Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# ==========================================
# 1. RESOURCE GROUP
# ==========================================
Write-Host "`n1. Resource Group" -ForegroundColor Cyan
Write-Host "==================" -ForegroundColor Cyan

Check-Resource -Name "Resource Group '$ResourceGroup'" -Check {
    $rg = az group show --name $ResourceGroup 2>$null | ConvertFrom-Json
    return $rg -ne $null
} -SuccessMessage "Location: brazilsouth" -FailMessage "Resource group not found"

# ==========================================
# 2. POSTGRESQL VM
# ==========================================
Write-Host "`n2. PostgreSQL VM" -ForegroundColor Cyan
Write-Host "=================" -ForegroundColor Cyan

$vmExists = Check-Resource -Name "VM '$PostgreSQLVMName'" -Check {
    $vm = az vm show -g $ResourceGroup -n $PostgreSQLVMName 2>$null | ConvertFrom-Json
    return $vm -ne $null
} -FailMessage "VM not found"

if ($vmExists) {
    $vmDetails = az vm show -g $ResourceGroup -n $PostgreSQLVMName | ConvertFrom-Json
    Write-Host "  Size: $($vmDetails.hardwareProfile.vmSize)" -ForegroundColor Gray
    Write-Host "  OS: Ubuntu Server 22.04" -ForegroundColor Gray
    Write-Host "  Status: " -NoNewline -ForegroundColor Gray
    
    $vmStatus = az vm get-instance-view -g $ResourceGroup -n $PostgreSQLVMName --query "instanceView.statuses[?starts_with(code, 'PowerState/')].displayStatus" -o tsv
    if ($vmStatus -eq "VM running") {
        Write-Host "$vmStatus ✓" -ForegroundColor Green
    }
    else {
        Write-Host "$vmStatus ✗" -ForegroundColor Red
        $script:errors += "VM is not running: $vmStatus"
    }
}

Check-Resource -Name "VM Public IP" -Check {
    $ip = az vm list-ip-addresses -g $ResourceGroup -n $PostgreSQLVMName --query "[0].virtualMachine.network.publicIpAddresses[0].ipAddress" -o tsv
    if ($ip -eq $DBHost) {
        Write-Host "  IP: $ip" -ForegroundColor Gray
        return $true
    }
    return $false
} -FailMessage "Public IP mismatch or not found"

# ==========================================
# 3. NETWORK SECURITY GROUP
# ==========================================
Write-Host "`n3. Network Security" -ForegroundColor Cyan
Write-Host "====================" -ForegroundColor Cyan

Check-Resource -Name "NSG Rules for PostgreSQL" -Check {
    $rules = az network nsg rule list -g $ResourceGroup --nsg-name "$PostgreSQLVMName-nsg" 2>$null | ConvertFrom-Json
    $postgresRule = $rules | Where-Object { $_.destinationPortRange -eq "5432" -and $_.access -eq "Allow" }
    $sshRule = $rules | Where-Object { $_.destinationPortRange -eq "22" -and $_.access -eq "Allow" }
    
    if ($postgresRule -and $sshRule) {
        Write-Host "  Port 5432 (PostgreSQL): Open ✓" -ForegroundColor Gray
        Write-Host "  Port 22 (SSH): Open ✓" -ForegroundColor Gray
        return $true
    }
    return $false
} -FailMessage "Required NSG rules not found"

# ==========================================
# 4. POSTGRESQL DATABASE
# ==========================================
Write-Host "`n4. PostgreSQL Database" -ForegroundColor Cyan
Write-Host "======================" -ForegroundColor Cyan

Check-Resource -Name "PostgreSQL Service" -Check {
    $result = az vm run-command invoke -g $ResourceGroup -n $PostgreSQLVMName `
        --command-id RunShellScript `
        --scripts "sudo systemctl is-active postgresql" `
        --query 'value[0].message' -o tsv 2>$null
    
    return $result -match "active"
} -SuccessMessage "PostgreSQL service is active" -FailMessage "PostgreSQL service is not active"

Check-Resource -Name "Database '$DBName'" -Check {
    $result = az vm run-command invoke -g $ResourceGroup -n $PostgreSQLVMName `
        --command-id RunShellScript `
        --scripts "sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -w '$DBName'" `
        --query 'value[0].message' -o tsv 2>$null
    
    return $result -match $DBName
} -SuccessMessage "Database exists" -FailMessage "Database '$DBName' not found"

Check-Resource -Name "Database User '$DBUser'" -Check {
    $result = az vm run-command invoke -g $ResourceGroup -n $PostgreSQLVMName `
        --command-id RunShellScript `
        --scripts "sudo -u postgres psql -t -c '\du' | grep '$DBUser'" `
        --query 'value[0].message' -o tsv 2>$null
    
    return $result -match $DBUser
} -SuccessMessage "User exists" -FailMessage "User '$DBUser' not found"

Check-Resource -Name "Database Tables" -Check {
    $result = az vm run-command invoke -g $ResourceGroup -n $PostgreSQLVMName `
        --command-id RunShellScript `
        --scripts "sudo -u postgres psql -d '$DBName' -c '\dt'" `
        --query 'value[0].message' -o tsv 2>$null
    
    $hasNorma = $result -match "norma"
    $hasAdmins = $result -match "admins"
    
    if ($hasNorma -and $hasAdmins) {
        Write-Host "  Table 'norma': Found ✓" -ForegroundColor Gray
        Write-Host "  Table 'admins': Found ✓" -ForegroundColor Gray
        return $true
    }
    return $false
} -FailMessage "Required tables not found"

Check-Resource -Name "Database Extensions" -Check {
    $result = az vm run-command invoke -g $ResourceGroup -n $PostgreSQLVMName `
        --command-id RunShellScript `
        --scripts "sudo -u postgres psql -d '$DBName' -c '\dx'" `
        --query 'value[0].message' -o tsv 2>$null
    
    $hasUuid = $result -match "uuid-ossp"
    $hasTrgm = $result -match "pg_trgm"
    
    if ($hasUuid -and $hasTrgm) {
        Write-Host "  Extension 'uuid-ossp': Installed ✓" -ForegroundColor Gray
        Write-Host "  Extension 'pg_trgm': Installed ✓" -ForegroundColor Gray
        return $true
    }
    return $false
} -FailMessage "Required extensions not installed"

# ==========================================
# 5. APP SERVICE PLAN
# ==========================================
Write-Host "`n5. App Service Plan" -ForegroundColor Cyan
Write-Host "====================" -ForegroundColor Cyan

$planExists = Check-Resource -Name "App Service Plan '$AppServicePlan'" -Check {
    $plan = az appservice plan show -g $ResourceGroup -n $AppServicePlan 2>$null | ConvertFrom-Json
    return $plan -ne $null
} -FailMessage "App Service Plan not found"

if ($planExists) {
    $plan = az appservice plan show -g $ResourceGroup -n $AppServicePlan | ConvertFrom-Json
    Write-Host "  SKU: $($plan.sku.name) ($($plan.sku.tier))" -ForegroundColor Gray
    Write-Host "  OS: $($plan.kind)" -ForegroundColor Gray
    Write-Host "  Status: $($plan.status)" -ForegroundColor Gray
}

# ==========================================
# 6. WEB APP (API)
# ==========================================
Write-Host "`n6. Web App (API)" -ForegroundColor Cyan
Write-Host "================" -ForegroundColor Cyan

$webAppExists = Check-Resource -Name "Web App '$WebAppName'" -Check {
    $app = az webapp show -g $ResourceGroup -n $WebAppName 2>$null | ConvertFrom-Json
    return $app -ne $null
} -FailMessage "Web App not found"

if ($webAppExists) {
    $app = az webapp show -g $ResourceGroup -n $WebAppName | ConvertFrom-Json
    Write-Host "  URL: https://$($app.defaultHostName)" -ForegroundColor Gray
    Write-Host "  State: $($app.state)" -ForegroundColor Gray
    Write-Host "  Runtime: Python 3.12" -ForegroundColor Gray
    
    # Check app settings
    Write-Host "`n  Environment Variables:" -ForegroundColor Gray
    $settings = az webapp config appsettings list -g $ResourceGroup -n $WebAppName | ConvertFrom-Json
    
    $requiredSettings = @("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD", "JWT_SECRET")
    foreach ($setting in $requiredSettings) {
        $exists = $settings | Where-Object { $_.name -eq $setting }
        if ($exists) {
            Write-Host "    ${setting}: Configured ✓" -ForegroundColor Gray
        }
        else {
            Write-Host "    ${setting}: Missing ✗" -ForegroundColor Red
            $script:errors += "Environment variable '$setting' not configured"
        }
    }
}

# ==========================================
# 7. API HEALTH CHECK
# ==========================================
Write-Host "`n7. API Health Check" -ForegroundColor Cyan
Write-Host "====================" -ForegroundColor Cyan

Check-Resource -Name "API Health Endpoint" -Check {
    try {
        $response = Invoke-WebRequest -Uri "https://$WebAppName.azurewebsites.net/health" -Method Get -TimeoutSec 10 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            $content = $response.Content | ConvertFrom-Json
            Write-Host "  Response: $($content | ConvertTo-Json -Compress)" -ForegroundColor Gray
            return $true
        }
    }
    catch {
        return $false
    }
    return $false
} -FailMessage "API health check failed - API may not be running"

# ==========================================
# 8. STORAGE ACCOUNT
# ==========================================
Write-Host "`n8. Storage Account (Frontend)" -ForegroundColor Cyan
Write-Host "==============================" -ForegroundColor Cyan

$storageExists = Check-Resource -Name "Storage Account '$StorageAccount'" -Check {
    $storage = az storage account show -g $ResourceGroup -n $StorageAccount 2>$null | ConvertFrom-Json
    return $storage -ne $null
} -FailMessage "Storage account not found"

if ($storageExists) {
    $storage = az storage account show -g $ResourceGroup -n $StorageAccount | ConvertFrom-Json
    Write-Host "  URL: $($storage.primaryEndpoints.web)" -ForegroundColor Gray
    Write-Host "  SKU: $($storage.sku.name)" -ForegroundColor Gray
    
    Check-Resource -Name "Static Website Enabled" -Check {
        $props = az storage blob service-properties show --account-name $StorageAccount --query "staticWebsite.enabled" -o tsv 2>$null
        return $props -eq "true"
    } -SuccessMessage "Index: index.html, Error: index.html" -FailMessage "Static website not enabled"
    
    Check-Resource -Name "Frontend Files" -Check {
        $key = az storage account keys list -g $ResourceGroup --account-name $StorageAccount --query "[0].value" -o tsv
        $blobs = az storage blob list --account-name $StorageAccount --account-key $key --container-name '$web' --query "length(@)" -o tsv 2>$null
        
        if ($blobs -gt 0) {
            Write-Host "  Files uploaded: $blobs" -ForegroundColor Gray
            return $true
        }
        return $false
    } -FailMessage "No frontend files found"
}

# ==========================================
# 9. FRONTEND URL CHECK
# ==========================================
Write-Host "`n9. Frontend URL Check" -ForegroundColor Cyan
Write-Host "=====================" -ForegroundColor Cyan

Check-Resource -Name "Frontend Accessible" -Check {
    try {
        $response = Invoke-WebRequest -Uri "https://$StorageAccount.z15.web.core.windows.net" -Method Get -TimeoutSec 10 -UseBasicParsing
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
} -SuccessMessage "Frontend is accessible" -FailMessage "Frontend URL is not accessible"

# ==========================================
# SUMMARY
# ==========================================
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if ($errors.Count -eq 0 -and $warnings.Count -eq 0) {
    Write-Host "`n✅ All checks passed!" -ForegroundColor Green
    Write-Host "`nYour deployment is healthy and ready to use." -ForegroundColor Green
}
else {
    if ($errors.Count -gt 0) {
        Write-Host "`n❌ Errors Found: $($errors.Count)" -ForegroundColor Red
        foreach ($error in $errors) {
            Write-Host "  • $error" -ForegroundColor Red
        }
    }
    
    if ($warnings.Count -gt 0) {
        Write-Host "`n⚠️  Warnings: $($warnings.Count)" -ForegroundColor Yellow
        foreach ($warning in $warnings) {
            Write-Host "  • $warning" -ForegroundColor Yellow
        }
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "URLs:" -ForegroundColor Yellow
Write-Host "  API: https://$WebAppName.azurewebsites.net" -ForegroundColor White
Write-Host "  API Docs: https://$WebAppName.azurewebsites.net/docs" -ForegroundColor White
Write-Host "  Frontend: https://$StorageAccount.z15.web.core.windows.net" -ForegroundColor White
Write-Host ""
