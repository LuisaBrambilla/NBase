# Inicia a API em modo desenvolvimento (atualizações são recarregadas automaticamente).
# Uso: .\iniciar_api.ps1
# Ou no PowerShell: & ".\iniciar_api.ps1"

$ErrorActionPreference = "Stop"
$raiz = $PSScriptRoot

Set-Location $raiz

# Ativa o venv se existir
$venv = Join-Path $raiz "venv"
if (Test-Path $venv) {
    $activate = Join-Path $venv "Scripts\Activate.ps1"
    if (Test-Path $activate) {
        Write-Host "Ativando ambiente virtual..." -ForegroundColor Cyan
        & $activate
    }
}

Write-Host "Iniciando API (uvicorn com --reload). Pressione Ctrl+C para parar." -ForegroundColor Green
python -m uvicorn api.main:root_app --reload --host 127.0.0.1 --port 8000
