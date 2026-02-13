# Azure Deployment Script for Gen360 (Resoluções ANA)
# This script will deploy the FastAPI backend to Azure App Service
# and the frontend to Azure Storage Static Website

param(
    [string]$ResourceGroup = "DemoGoverno",
    [string]$Location = "brazilsouth",
    [string]$AppServicePlan = "asp-gen360",
    [string]$WebAppName = "app-gen360-api",
    [string]$StorageAccount = "stgen360frontend",
    [string]$PostgreSQLHost = "20.226.39.175",  # PostgreSQL VM IP
    [string]$PostgreSQLUser = "linuxuser",
    [string]$PostgreSQLPassword = "r!(hFarm96g5Ayb3INF6",
    [string]$DBName = "normas"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Gen360 - Azure Deployment Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Login to Azure
Write-Host "Step 1: Login to Azure" -ForegroundColor Yellow
Write-Host "Please complete the browser authentication..." -ForegroundColor Gray
az login --tenant 6b1db0da-c53f-48bf-b271-9297590ad872
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Azure login failed" -ForegroundColor Red
    exit 1
}

# Set subscription
Write-Host "Setting active subscription..." -ForegroundColor Gray
az account set --subscription "618a82e3-0571-4142-b50d-c8d2c34060ae"

Write-Host "✓ Logged in successfully" -ForegroundColor Green
Write-Host ""

# Step 2: Verify Resource Group Exists
Write-Host "Step 2: Verifying Resource Group" -ForegroundColor Yellow
$rgExists = az group exists --name $ResourceGroup
if ($rgExists -eq "true") {
    Write-Host "✓ Resource group '$ResourceGroup' exists" -ForegroundColor Green
}
else {
    Write-Host "Creating resource group '$ResourceGroup'..." -ForegroundColor Gray
    az group create --name $ResourceGroup --location $Location
    Write-Host "✓ Resource group created" -ForegroundColor Green
}
Write-Host ""

# Step 3: Create App Service Plan (Linux, Python)
Write-Host "Step 3: Creating App Service Plan" -ForegroundColor Yellow
az appservice plan create `
    --name $AppServicePlan `
    --resource-group $ResourceGroup `
    --location $Location `
    --is-linux `
    --sku B1

Write-Host "✓ App Service Plan created" -ForegroundColor Green
Write-Host ""

# Step 4: Create Web App
Write-Host "Step 4: Creating Web App for API" -ForegroundColor Yellow
az webapp create `
    --name $WebAppName `
    --resource-group $ResourceGroup `
    --plan $AppServicePlan `
    --runtime "PYTHON:3.12"

Write-Host "✓ Web App created" -ForegroundColor Green
Write-Host ""

# Step 5: Configure App Settings (Environment Variables)
Write-Host "Step 5: Configuring Application Settings" -ForegroundColor Yellow
Write-Host "Database Host: $PostgreSQLHost" -ForegroundColor Gray

$jwtSecret = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 64 | ForEach-Object { [char]$_ })

az webapp config appsettings set `
    --name $WebAppName `
    --resource-group $ResourceGroup `
    --settings `
    DB_HOST="$PostgreSQLHost" `
    DB_PORT="5432" `
    DB_NAME="$DBName" `
    DB_USER="$PostgreSQLUser" `
    DB_PASSWORD="$PostgreSQLPassword" `
    JWT_SECRET="$jwtSecret" `
    JWT_ALGORITHM="HS256" `
    JWT_EXPIRE_MINUTES="60" `
    MFA_ISSUER="Gen360Admin" `
    CORS_ORIGINS="https://$WebAppName.azurewebsites.net,https://$StorageAccount.z15.web.core.windows.net" `
    SCM_DO_BUILD_DURING_DEPLOYMENT="true" `
    WEBSITE_HTTPLOGGING_RETENTION_DAYS="7"

Write-Host "✓ App settings configured" -ForegroundColor Green
Write-Host ""

# Step 6: Configure startup command
Write-Host "Step 6: Configuring Startup Command" -ForegroundColor Yellow
az webapp config set `
    --name $WebAppName `
    --resource-group $ResourceGroup `
    --startup-file "gunicorn -w 4 -k uvicorn.workers.UvicornWorker api.main:app --bind=0.0.0.0:8000 --timeout 600"

Write-Host "✓ Startup command configured" -ForegroundColor Green
Write-Host ""

# Step 7: Deploy the API code from local files
Write-Host "Step 7: Deploying API Code from Local Files" -ForegroundColor Yellow
Write-Host "Creating deployment package..." -ForegroundColor Gray

# Create a temporary directory for deployment
$timestamp = Get-Date -Format 'yyyyMMddHHmmss'
$tempDir = Join-Path $env:TEMP "gen360_deploy_$timestamp"
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

Write-Host "Copying files to temporary directory..." -ForegroundColor Gray
# Copy necessary files from parent directory (go up from setup/)
$sourceDir = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrEmpty($sourceDir)) {
    $sourceDir = "."
}

Copy-Item -Path "$sourceDir\api" -Destination $tempDir -Recurse -Force
Copy-Item -Path "$sourceDir\db" -Destination $tempDir -Recurse -Force
Copy-Item -Path "$sourceDir\requirements.txt" -Destination $tempDir -Force
Copy-Item -Path "$sourceDir\runtime.txt" -Destination $tempDir -Force -ErrorAction SilentlyContinue
Copy-Item -Path "$sourceDir\startup.sh" -Destination $tempDir -Force -ErrorAction SilentlyContinue

Write-Host "Creating ZIP archive..." -ForegroundColor Gray
# Create zip file
$zipPath = Join-Path $env:TEMP "gen360_deploy_$timestamp.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }

Compress-Archive -Path "$tempDir\*" -DestinationPath $zipPath -Force

Write-Host "Uploading to Azure App Service..." -ForegroundColor Gray
az webapp deployment source config-zip `
    --resource-group $ResourceGroup `
    --name $WebAppName `
    --src $zipPath

# Clean up
Write-Host "Cleaning up temporary files..." -ForegroundColor Gray
Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $zipPath -Force -ErrorAction SilentlyContinue

Write-Host "✓ API deployed successfully from local files" -ForegroundColor Green
Write-Host ""

# Step 8: Create Storage Account for Frontend
Write-Host "Step 8: Creating Storage Account for Frontend" -ForegroundColor Yellow
az storage account create `
    --name $StorageAccount `
    --resource-group $ResourceGroup `
    --location $Location `
    --sku Standard_LRS `
    --kind StorageV2

Write-Host "✓ Storage account created" -ForegroundColor Green
Write-Host ""

# Step 9: Enable Static Website Hosting
Write-Host "Step 9: Enabling Static Website Hosting" -ForegroundColor Yellow
az storage blob service-properties update `
    --account-name $StorageAccount `
    --static-website `
    --index-document index.html `
    --404-document index.html

Write-Host "✓ Static website enabled" -ForegroundColor Green
Write-Host ""

# Step 10: Upload Frontend Files
Write-Host "Step 10: Uploading Frontend Files" -ForegroundColor Yellow
$storageKey = az storage account keys list --account-name $StorageAccount --resource-group $ResourceGroup --query "[0].value" -o tsv

# Get frontend source directory
$frontendSource = Join-Path $sourceDir "admin_frontend"
if (-not (Test-Path $frontendSource)) {
    $frontendSource = ".\admin_frontend"
}

Write-Host "Uploading from: $frontendSource" -ForegroundColor Gray
az storage blob upload-batch `
    --account-name $StorageAccount `
    --account-key $storageKey `
    --destination '$web' `
    --source $frontendSource `
    --pattern "*" `
    --overwrite

Write-Host "✓ Frontend files uploaded" -ForegroundColor Green
Write-Host ""

# Get URLs
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "API URL: " -NoNewline; Write-Host "https://$WebAppName.azurewebsites.net" -ForegroundColor Cyan
Write-Host "Frontend URL: " -NoNewline; Write-Host "https://$StorageAccount.z15.web.core.windows.net" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. PostgreSQL VM firewall is already configured (port 5432 open)" -ForegroundColor Gray
Write-Host "2. Database schema already deployed to 'normas' database" -ForegroundColor Gray
Write-Host "3. Update frontend API URL in admin_frontend/app.js if needed" -ForegroundColor Gray
Write-Host "4. Test the API: https://$WebAppName.azurewebsites.net/health" -ForegroundColor Gray
Write-Host "5. Register first admin user via frontend" -ForegroundColor Gray
Write-Host ""
Write-Host "Resource Group: DemoGoverno" -ForegroundColor Gray
Write-Host "Deployment Source: Local files (ZIP upload)" -ForegroundColor Gray
Write-Host ""
