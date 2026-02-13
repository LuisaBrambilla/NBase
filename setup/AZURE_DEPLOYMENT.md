# Azure Deployment Guide - Gen360 (Resoluções ANA)

## Prerequisites
- Azure subscription: `618a82e3-0571-4142-b50d-c8d2c34060ae`
- Azure CLI installed and working
- PostgreSQL VM with credentials:
  - User: `linuxuser`
  - Password: `r!(hFarm96g5Ayb3INF6`
  - Database: `normas`

## Quick Deployment

### Option 1: Automated Deployment (Recommended)

Run the deployment script:

```powershell
.\deploy_azure.ps1 -PostgreSQLHost "YOUR_POSTGRESQL_VM_IP"
```

Replace `YOUR_POSTGRESQL_VM_IP` with your actual PostgreSQL VM IP address or hostname.

---

### Option 2: Manual Step-by-Step Deployment

#### 1. Login to Azure

```powershell
az login --tenant 6b1db0da-c53f-48bf-b271-9297590ad872
az account set --subscription "618a82e3-0571-4142-b50d-c8d2c34060ae"
```

#### 2. Set Variables

```powershell
$rg = "rg-gen360"
$location = "brazilsouth"
$plan = "asp-gen360"
$webapp = "app-gen360-api"
$storage = "stgen360frontend"
$dbHost = "YOUR_POSTGRESQL_VM_IP"  # Replace with your PostgreSQL VM IP
```

#### 3. Create Resource Group

```powershell
az group create --name $rg --location $location
```

#### 4. Create App Service Plan (Linux + Python)

```powershell
az appservice plan create `
    --name $plan `
    --resource-group $rg `
    --location $location `
    --is-linux `
    --sku B1
```

#### 5. Create Web App

```powershell
az webapp create `
    --name $webapp `
    --resource-group $rg `
    --plan $plan `
    --runtime "PYTHON:3.12"
```

#### 6. Configure Environment Variables

```powershell
# Generate a random JWT secret
$jwtSecret = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 64 | ForEach-Object {[char]$_})

az webapp config appsettings set `
    --name $webapp `
    --resource-group $rg `
    --settings `
        DB_HOST="$dbHost" `
        DB_PORT="5432" `
        DB_NAME="normas" `
        DB_USER="linuxuser" `
        DB_PASSWORD="r!(hFarm96g5Ayb3INF6" `
        JWT_SECRET="$jwtSecret" `
        JWT_ALGORITHM="HS256" `
        JWT_EXPIRE_MINUTES="60" `
        MFA_ISSUER="Gen360Admin" `
        CORS_ORIGINS="*" `
        SCM_DO_BUILD_DURING_DEPLOYMENT="true"
```

#### 7. Configure Startup Command

```powershell
az webapp config set `
    --name $webapp `
    --resource-group $rg `
    --startup-file "gunicorn -w 4 -k uvicorn.workers.UvicornWorker api.main:app --bind=0.0.0.0:8000 --timeout 600"
```

#### 8. Deploy API Code (Zip Deployment)

```powershell
# Create deployment package
$tempDir = "C:\temp\gen360_deploy"
New-Item -ItemType Directory -Path $tempDir -Force

# Copy files
Copy-Item -Path ".\api" -Destination $tempDir -Recurse -Force
Copy-Item -Path ".\db" -Destination $tempDir -Recurse -Force
Copy-Item -Path ".\requirements.txt" -Destination $tempDir -Force

# Create zip
$zipPath = "C:\temp\gen360_deploy.zip"
Compress-Archive -Path "$tempDir\*" -DestinationPath $zipPath -Force

# Deploy
az webapp deployment source config-zip `
    --resource-group $rg `
    --name $webapp `
    --src $zipPath

# Clean up
Remove-Item $tempDir -Recurse -Force
Remove-Item $zipPath -Force
```

#### 9. Setup PostgreSQL Database

Connect to your PostgreSQL VM and run:

```sql
-- Connect to PostgreSQL
psql -U linuxuser -d postgres

-- Create database
CREATE DATABASE normas;

-- Connect to the database
\c normas

-- Run the schema (copy content from db/models.sql)
-- Or run: psql -U linuxuser -d normas -f db/models.sql
```

#### 10. Configure PostgreSQL Firewall

Allow Azure services to connect to your PostgreSQL VM:

```bash
# On your PostgreSQL VM, edit pg_hba.conf
sudo nano /etc/postgresql/*/main/pg_hba.conf

# Add this line (replace with Azure Web App outbound IPs):
host    normas    linuxuser    0.0.0.0/0    md5

# Restart PostgreSQL
sudo systemctl restart postgresql
```

#### 11. Create Storage Account for Frontend

```powershell
az storage account create `
    --name $storage `
    --resource-group $rg `
    --location $location `
    --sku Standard_LRS `
    --kind StorageV2
```

#### 12. Enable Static Website Hosting

```powershell
az storage blob service-properties update `
    --account-name $storage `
    --static-website `
    --index-document index.html `
    --404-document index.html
```

#### 13. Update Frontend Configuration

Edit `admin_frontend/app.js` and update the API URL:

```javascript
const API_BASE_URL = window.API_BASE_URL || "https://app-gen360-api.azurewebsites.net";
```

#### 14. Upload Frontend Files

```powershell
# Get storage account key
$key = az storage account keys list --account-name $storage --resource-group $rg --query "[0].value" -o tsv

# Upload files
az storage blob upload-batch `
    --account-name $storage `
    --account-key $key `
    --destination '$web' `
    --source ".\admin_frontend"
```

---

## Post-Deployment

### 1. Test API Health

Visit: `https://app-gen360-api.azurewebsites.net/health`

Should return: `{"status": "ok"}`

### 2. Test Frontend

Visit: `https://stgen360frontend.z15.web.core.windows.net`

### 3. View Logs

```powershell
# Stream logs
az webapp log tail --name $webapp --resource-group $rg

# Or view in Azure Portal:
# https://portal.azure.com -> App Services -> app-gen360-api -> Log stream
```

### 4. Register First Admin User

1. Go to frontend admin login page
2. Click "Register"
3. Create your admin account with MFA

---

## Troubleshooting

### API Returns 500 Error
- Check database connection in App Service logs
- Verify PostgreSQL VM is reachable from Azure
- Check environment variables are set correctly

### Database Connection Failed
- Verify PostgreSQL is running on VM
- Check firewall rules allow Azure App Service IPs
- Test connection: `psql -h $dbHost -U linuxuser -d normas`

### Frontend Can't Connect to API
- Check CORS settings in API
- Verify API URL in `app.js`
- Check browser console for errors

---

## Resource Names

- Resource Group: `rg-gen360`
- App Service Plan: `asp-gen360`
- Web App (API): `app-gen360-api`
- Storage Account (Frontend): `stgen360frontend`
- Database: `normas`

---

## URLs

- API: `https://app-gen360-api.azurewebsites.net`
- API Health Check: `https://app-gen360-api.azurewebsites.net/health`
- API Docs: `https://app-gen360-api.azurewebsites.net/docs`
- Frontend: `https://stgen360frontend.z15.web.core.windows.net`

---

## Cost Estimation

- App Service Plan B1: ~$13/month
- Storage Account: ~$1/month
- PostgreSQL VM: Variable (you already have this)
- **Total**: ~$14/month + PostgreSQL VM costs
