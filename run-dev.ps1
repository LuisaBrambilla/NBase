# =============================================================
# Gen360 — Local Dev Environment Startup Script
# Run from project root: .\run-dev.ps1
# =============================================================

param(
    [switch]$Reset,       # Destroy and recreate container from scratch
    [switch]$FrontendOnly # Only start the frontend server
)

$ErrorActionPreference = "Continue"
$ProjectRoot = $PSScriptRoot
if (-not $ProjectRoot) { $ProjectRoot = Get-Location }
Set-Location $ProjectRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Gen360 — Local Dev Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# -----------------------------------------------------------------
# 1. Check prerequisites
# -----------------------------------------------------------------
Write-Host "[1/7] Checking prerequisites..." -ForegroundColor Yellow

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "  ERROR: Python not found. Install Python 3.12+ from python.org" -ForegroundColor Red
    exit 1
}
$pyVer = python --version 2>&1
Write-Host "  Python: $pyVer" -ForegroundColor Gray

$docker = Get-Command docker -ErrorAction SilentlyContinue
if (-not $docker) {
    Write-Host "  ERROR: Docker not found. Install Docker Desktop." -ForegroundColor Red
    exit 1
}
Write-Host "  Docker: $(docker --version 2>&1)" -ForegroundColor Gray
Write-Host ""

# -----------------------------------------------------------------
# 2. Ensure Docker Desktop is running
# -----------------------------------------------------------------
Write-Host "[2/7] Ensuring Docker engine is running..." -ForegroundColor Yellow

$dockerOk = $false
try {
    $info = docker info 2>&1
    if ($LASTEXITCODE -eq 0 -and $info -notmatch "Cannot connect|failed to connect") {
        $dockerOk = $true
    }
} catch {}

if (-not $dockerOk) {
    Write-Host "  Docker engine not responding. Starting Docker Desktop..." -ForegroundColor Gray
    $ddPaths = @(
        "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
        "${env:ProgramFiles(x86)}\Docker\Docker\Docker Desktop.exe",
        "$env:LOCALAPPDATA\Docker\Docker Desktop.exe"
    )
    $started = $false
    foreach ($p in $ddPaths) {
        if (Test-Path $p) {
            Start-Process $p
            $started = $true
            break
        }
    }
    if (-not $started) {
        Write-Host "  ERROR: Docker Desktop not found. Please start it manually." -ForegroundColor Red
        exit 1
    }

    # Wait up to 60 seconds
    for ($i = 1; $i -le 12; $i++) {
        Start-Sleep -Seconds 5
        try {
            $info = docker info 2>&1
            if ($LASTEXITCODE -eq 0 -and $info -notmatch "Cannot connect|failed to connect") {
                $dockerOk = $true
                Write-Host "  Docker ready after $($i * 5)s" -ForegroundColor Green
                break
            }
        } catch {}
        Write-Host "  Waiting... ($($i * 5)s)" -ForegroundColor Gray
    }
    if (-not $dockerOk) {
        # Try switching context
        Write-Host "  Trying alternate Docker context..." -ForegroundColor Gray
        docker context use desktop-linux 2>$null
        if ($LASTEXITCODE -ne 0) { docker context use default 2>$null }
        $info = docker info 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  ERROR: Docker engine failed to start." -ForegroundColor Red
            exit 1
        }
    }
}
Write-Host "  Docker engine OK" -ForegroundColor Green
Write-Host ""

# -----------------------------------------------------------------
# 3. PostgreSQL container
# -----------------------------------------------------------------
Write-Host "[3/7] Setting up PostgreSQL container..." -ForegroundColor Yellow

$containerName = "gen360-postgres"
$pgImage = "postgres:16"
$pgPort = "5432"
$pgDb = "normas"
$pgUser = "postgres"
$pgPass = "Newpr2026@"

# Reset if requested
if ($Reset) {
    Write-Host "  --Reset flag: destroying existing container..." -ForegroundColor Gray
    docker rm -f $containerName 2>$null | Out-Null
}

# Check if container exists
$existing = docker ps -a --filter "name=$containerName" --format "{{.Status}}" 2>$null

if (-not $existing) {
    # Create new container
    Write-Host "  Creating container '$containerName'..." -ForegroundColor Gray
    docker run -d --name $containerName `
        -e POSTGRES_DB=$pgDb `
        -e POSTGRES_USER=$pgUser `
        -e POSTGRES_PASSWORD=$pgPass `
        -p "${pgPort}:5432" `
        $pgImage 2>&1 | Out-Null

    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ERROR: Failed to create container." -ForegroundColor Red
        exit 1
    }
    Write-Host "  Container created. Waiting for readiness..." -ForegroundColor Gray
    Start-Sleep -Seconds 5

    # Wait for PG ready
    for ($i = 1; $i -le 10; $i++) {
        $ready = docker exec $containerName pg_isready -U $pgUser 2>&1
        if ($ready -match "accepting connections") { break }
        Start-Sleep -Seconds 2
    }

    # Apply schema + migrations
    Write-Host "  Applying database schema..." -ForegroundColor Gray
    Get-Content "$ProjectRoot\db\models.sql" -Raw | docker exec -i $containerName psql -U $pgUser -d $pgDb 2>&1 | Out-Null
    Get-Content "$ProjectRoot\db\migracoes\002_origem_dodf.sql" -Raw | docker exec -i $containerName psql -U $pgUser -d $pgDb 2>&1 | Out-Null
    Get-Content "$ProjectRoot\db\migracoes\003_admin_mfa.sql" -Raw | docker exec -i $containerName psql -U $pgUser -d $pgDb 2>&1 | Out-Null
    Get-Content "$ProjectRoot\db\migracoes\004_verificacao_normas.sql" -Raw | docker exec -i $containerName psql -U $pgUser -d $pgDb 2>&1 | Out-Null
    Write-Host "  Schema and migrations applied" -ForegroundColor Green

} elseif ($existing -match "^Up") {
    Write-Host "  Container already running" -ForegroundColor Green
} else {
    Write-Host "  Container exists but stopped. Starting..." -ForegroundColor Gray
    docker start $containerName 2>&1 | Out-Null
    Start-Sleep -Seconds 3
    Write-Host "  Container started" -ForegroundColor Green
}

# Final readiness check
$ready = docker exec $containerName pg_isready -U $pgUser 2>&1
if ($ready -match "accepting connections") {
    Write-Host "  PostgreSQL accepting connections on port $pgPort" -ForegroundColor Green
} else {
    Write-Host "  WARNING: PostgreSQL may not be ready yet" -ForegroundColor Yellow
}
Write-Host ""

# -----------------------------------------------------------------
# 4. Install Python dependencies
# -----------------------------------------------------------------
Write-Host "[4/7] Checking Python dependencies..." -ForegroundColor Yellow
$missing = $false
try {
    python -c "import fastapi, uvicorn, psycopg2, pydantic" 2>$null
    if ($LASTEXITCODE -ne 0) { $missing = $true }
} catch { $missing = $true }

if ($missing) {
    Write-Host "  Installing dependencies..." -ForegroundColor Gray
    pip install -r "$ProjectRoot\requirements.txt" --quiet 2>&1 | Out-Null
    Write-Host "  Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "  All dependencies present" -ForegroundColor Green
}
Write-Host ""

# -----------------------------------------------------------------
# 5. Set environment variables
# -----------------------------------------------------------------
Write-Host "[5/7] Setting environment variables..." -ForegroundColor Yellow

$env:DB_HOST = "localhost"
$env:DB_PORT = $pgPort
$env:DB_NAME = $pgDb
$env:DB_USER = $pgUser
$env:DB_PASSWORD = $pgPass
$env:JWT_SECRET = "local-dev-secret"
$env:JWT_EXPIRE_MINUTES = "60"
$env:MFA_ISSUER = "ResolucoesAdmin"
$env:CORS_ORIGINS = "*"

Write-Host "  DB_HOST=localhost  DB_PORT=$pgPort  DB_NAME=$pgDb  DB_USER=$pgUser" -ForegroundColor Gray
Write-Host "  JWT_SECRET=local-dev-secret  CORS_ORIGINS=*" -ForegroundColor Gray
Write-Host "  Environment configured" -ForegroundColor Green
Write-Host ""

# -----------------------------------------------------------------
# 6. Start frontend server (background)
# -----------------------------------------------------------------
if (-not $FrontendOnly) {
    Write-Host "[6/7] Starting frontend server (port 3000)..." -ForegroundColor Yellow

    # Check if port 3000 is free
    $port3000 = netstat -ano 2>$null | Select-String ":3000.*LISTENING"
    if ($port3000) {
        Write-Host "  Port 3000 already in use — skipping frontend server" -ForegroundColor Yellow
    } else {
        $frontendJob = Start-Process python -ArgumentList "-m http.server 3000 --directory `"$ProjectRoot\admin_frontend`"" -PassThru -WindowStyle Minimized
        Write-Host "  Frontend server started (PID: $($frontendJob.Id))" -ForegroundColor Green
    }
    Write-Host ""
}

# -----------------------------------------------------------------
# 7. Start API server
# -----------------------------------------------------------------
Write-Host "[7/7] Starting API server (port 8000)..." -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  READY" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  API:      http://localhost:8000" -ForegroundColor White
Write-Host "  Swagger:  http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Health:   http://localhost:8000/health" -ForegroundColor White
Write-Host "  Frontend: http://localhost:3000" -ForegroundColor White
Write-Host ""
Write-Host "  Press Ctrl+C to stop the API server." -ForegroundColor Gray
Write-Host ""

python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
