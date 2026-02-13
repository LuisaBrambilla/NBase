param(
    [string]$SubscriptionId = "618a82e3-0571-4142-b50d-c8d2c34060ae",
    [string]$ResourceGroup = "DemoGoverno",
    [string]$WebAppName = "app-gen360-api",
    [string]$StorageAccount = "stgen360frontend",
    [string]$SourceDir = "",
    [switch]$UseStorageKey,
    [string]$StorageAccountKey = ""
)

$ErrorActionPreference = "Stop"

function Invoke-AzCli {
    param([string[]]$Arguments)
    & az @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Azure CLI command failed: az $($Arguments -join ' ')"
    }
}

function Ensure-AzLogin {
    param([string]$SubscriptionId)
    $loggedIn = $false
    try {
        & az account show --query "id" -o tsv | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $loggedIn = $true
        }
    }
    catch {
        $loggedIn = $false
    }

    if (-not $loggedIn) {
        Write-Host "Azure CLI not authenticated. Running az login --use-device-code..." -ForegroundColor Yellow
        Invoke-AzCli @("login", "--use-device-code") | Out-Null
    }

    Write-Host "Setting subscription $SubscriptionId" -ForegroundColor Cyan
    Invoke-AzCli @("account", "set", "--subscription", $SubscriptionId) | Out-Null
}

if (-not $SourceDir) {
    $repoRoot = (Resolve-Path (Join-Path $PSScriptRoot ".." )).Path
    $SourceDir = $repoRoot
}

$apiSource = Join-Path $SourceDir "api"
$dbSource = Join-Path $SourceDir "db"
$requirementsPath = Join-Path $SourceDir "requirements.txt"
$runtimePath = Join-Path $SourceDir "runtime.txt"
$startupScript = Join-Path $SourceDir "startup.sh"
$frontendSource = Join-Path $SourceDir "admin_frontend"

if (-not (Test-Path $apiSource)) { throw "API source folder not found: $apiSource" }
if (-not (Test-Path $dbSource)) { throw "DB source folder not found: $dbSource" }
if (-not (Test-Path $requirementsPath)) { throw "requirements.txt not found at $requirementsPath" }
if (-not (Test-Path $frontendSource)) { throw "admin_frontend folder not found: $frontendSource" }

Ensure-AzLogin -SubscriptionId $SubscriptionId

$timestamp = Get-Date -Format 'yyyyMMddHHmmss'
$tempDir = Join-Path $env:TEMP "gen360_deploy_$timestamp"
$zipPath = Join-Path $env:TEMP "gen360_deploy_$timestamp.zip"

Write-Host "Creating temp directory $tempDir" -ForegroundColor Cyan
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

Write-Host "Staging API files..." -ForegroundColor Cyan
Copy-Item -Path $apiSource -Destination $tempDir -Recurse -Force
Copy-Item -Path $dbSource -Destination $tempDir -Recurse -Force
Copy-Item -Path $requirementsPath -Destination $tempDir -Force
if (Test-Path $runtimePath) { Copy-Item -Path $runtimePath -Destination $tempDir -Force }
if (Test-Path $startupScript) { Copy-Item -Path $startupScript -Destination $tempDir -Force }

if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Write-Host "Creating deployment package $zipPath" -ForegroundColor Cyan
Compress-Archive -Path (Join-Path $tempDir '*') -DestinationPath $zipPath -Force

try {
    Write-Host "Deploying API to $WebAppName" -ForegroundColor Green
    Invoke-AzCli @(
        "webapp", "deploy",
        "--resource-group", $ResourceGroup,
        "--name", $WebAppName,
        "--type", "zip",
        "--src-path", $zipPath,
        "--target-path", "site/wwwroot"
    ) | Out-Null
}
catch {
    throw "API deployment failed: $_"
}
finally {
    Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
}

Write-Host "Uploading admin frontend to static site ($StorageAccount)" -ForegroundColor Green
$uploadArgs = @(
    "storage", "blob", "upload-batch",
    "--account-name", $StorageAccount,
    "--destination", "`$web",
    "--source", $frontendSource,
    "--overwrite", "true"
)

if ($UseStorageKey -or $StorageAccountKey) {
    if (-not $StorageAccountKey) {
        Write-Host "Retrieving storage account key..." -ForegroundColor Cyan
        $StorageAccountKey = (& az storage account keys list --account-name $StorageAccount --resource-group $ResourceGroup --query "[0].value" -o tsv)
        if ($LASTEXITCODE -ne 0 -or -not $StorageAccountKey) {
            throw "Failed to retrieve storage account key"
        }
    }
    $uploadArgs += @("--account-key", $StorageAccountKey)
}
else {
    $uploadArgs += @("--auth-mode", "login")
}

Invoke-AzCli $uploadArgs | Out-Null

Write-Host "Deployment complete." -ForegroundColor Green
Write-Host "API: https://$WebAppName.azurewebsites.net" -ForegroundColor Green
Write-Host "Frontend: https://$StorageAccount.z15.web.core.windows.net" -ForegroundColor Green
