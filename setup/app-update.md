# Gen360 App Update Playbook

_Last updated: 2026-02-12_

This checklist captures the exact sequence we used to refresh both the FastAPI backend (App Service) and the admin frontend (Azure Storage static site). Reuse it for future deployments.

## 1. Authenticate and Select Subscription

```powershell
az login --use-device-code
az account list -o table            # confirm available subs
az account set --subscription "618a82e3-0571-4142-b50d-c8d2c34060ae"
az account show -o table
```

## 2. Deploy Latest API Code to App Service

```powershell
# Variables
$timestamp = Get-Date -Format 'yyyyMMddHHmmss'
$sourceDir = "F:/TECBIS/GitHub/Gen360"
$tempDir   = Join-Path $env:TEMP "gen360_deploy_$timestamp"
$zipPath   = Join-Path $env:TEMP "gen360_deploy_$timestamp.zip"

# Stage files
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
Copy-Item "$sourceDir/api" -Destination $tempDir -Recurse -Force
Copy-Item "$sourceDir/db" -Destination $tempDir -Recurse -Force
Copy-Item "$sourceDir/requirements.txt" -Destination $tempDir -Force
if (Test-Path "$sourceDir/runtime.txt") { Copy-Item "$sourceDir/runtime.txt" -Destination $tempDir -Force }
if (Test-Path "$sourceDir/startup.sh") { Copy-Item "$sourceDir/startup.sh" -Destination $tempDir -Force }

# Package
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path "$tempDir/*" -DestinationPath $zipPath -Force

# Deploy (zip push)
az webapp deployment source config-zip `
    --resource-group DemoGoverno `
    --name app-gen360-api `
    --src $zipPath

# Clean up
Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
```

> **Note:** CLI now recommends `az webapp deploy` instead of `config-zip`; if preferred, swap commands but keep the same ZIP file.

## 3. Upload Admin Frontend to Static Website

```powershell
# Option A: Use RBAC (requires Storage Blob Data Contributor)
az storage blob upload-batch `
    --account-name stgen360frontend `
    --auth-mode login `
    --destination '$web' `
    --source admin_frontend `
    --overwrite true
```

```powershell
# Option B: Use account key (works even without RBAC)
$storageKey = az storage account keys list `
    --account-name stgen360frontend `
    --resource-group DemoGoverno `
    --query "[0].value" -o tsv

az storage blob upload-batch `
    --account-name stgen360frontend `
    --account-key $storageKey `
    --destination '$web' `
    --source admin_frontend `
    --overwrite true
```

## 4. Post-Deployment Checks

1. **API health:** `curl https://app-gen360-api.azurewebsites.net/health` and `/health/db`.
2. **Static site cache:** Hard refresh `https://stgen360frontend.z15.web.core.windows.net/admin_login.html` (or purge CDN if fronted).
3. **Login flow:** Verify admin login posts to `https://app-gen360-api.azurewebsites.net/admin/login` (check Network tab).
4. **Logs:** `az webapp log tail --name app-gen360-api --resource-group DemoGoverno` while exercising critical paths.

Keeping this document updated ensures repeatable deployments without digging through history each time.
