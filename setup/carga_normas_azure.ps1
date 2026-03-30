# =============================================================================
# Carga de normas para a base PostgreSQL no Azure (VM postgresql-vm / normas)
# =============================================================================
# PRÉ-REQUISITOS:
#   1. Ficheiro .env na RAIZ do projeto com DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
#      apontando para o servidor (ex.: DB_HOST=20.226.39.175, DB_NAME=normas).
#   2. Migração origem 'arespcj' aplicada na base (CHECK em norma_origem_check).
#   3. venv criado e dependências: pip install -r requirements.txt
#
# USO (PowerShell, na pasta setup OU na raiz):
#   cd "...\Gen360"
#   .\setup\carga_normas_azure.ps1
#
#   Apenas ARES-PCJ:
#   .\setup\carga_normas_azure.ps1 -SoAresPcj
#
#   ARES + ANA (sem DOU):
#   .\setup\carga_normas_azure.ps1 -SoAresPcj -SoAnaGovbr
#
#   Apenas DOU (precisa de -DouBaseUrl):
#   .\setup\carga_normas_azure.ps1 -SoDou -DouBaseUrl "https://..." -AnoInicio 2023 -AnoFim 2024
#
#   Apenas ANA (gov.br — resoluções regulatórias):
#   .\setup\carga_normas_azure.ps1 -SoAnaGovbr
#   .\setup\carga_normas_azure.ps1 -SoAnaGovbr -LimiteAnaGovbr 50
# =============================================================================

param(
    [switch]$SoAresPcj,
    [switch]$SoDou,
    [switch]$SoAnaGovbr,
    [string]$DouBaseUrl = "",
    [int]$AnoInicio = 2023,
    [int]$AnoFim = 2024,
    [int[]]$Meses = @(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12),
    [int]$LimiteAresPcj = 0,
    [switch]$BaixarTudoAresPcj,
    [int]$LimiteAnaGovbr = 0
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $Root "requirements.txt"))) {
    $Root = $PSScriptRoot
}

Set-Location $Root
Write-Host "Pasta do projeto: $Root" -ForegroundColor Cyan

$VenvPython = Join-Path $Root "venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "ERRO: venv não encontrado. Crie com: python -m venv venv" -ForegroundColor Red
    exit 1
}

$EnvFile = Join-Path $Root ".env"
if (-not (Test-Path $EnvFile)) {
    Write-Host "ERRO: .env não encontrado na raiz do projeto." -ForegroundColor Red
    exit 1
}

function Invoke-Carga {
    param([string[]]$Args)
    Write-Host "`n>> $($Args -join ' ')" -ForegroundColor Yellow
    & $VenvPython @Args
    if ($LASTEXITCODE -ne 0) {
        throw "Comando falhou com código $LASTEXITCODE"
    }
}

$explicit = @()
if ($SoAresPcj) { $explicit += "ares" }
if ($SoDou) { $explicit += "dou" }
if ($SoAnaGovbr) { $explicit += "ana" }

if ($explicit.Count -eq 0) {
    $doAres = $true
    $doDou = $true
    $doAnaGovbr = $false
}
else {
    $doAres = $explicit -contains "ares"
    $doDou = $explicit -contains "dou"
    $doAnaGovbr = $explicit -contains "ana"
}

# ---------------------------------------------------------------------------
# ARES-PCJ: lista no site, PDF -> Word/HTML, grava em norma (origem=arespcj)
# ---------------------------------------------------------------------------
if ($doAres) {
    Write-Host "`n=== ARES-PCJ (coletar_arespcj) ===" -ForegroundColor Green
    $argsAres = @("-m", "scripts.coletar_arespcj")
    if ($LimiteAresPcj -gt 0) {
        $argsAres += "--limit", "$LimiteAresPcj"
    }
    if ($BaixarTudoAresPcj) {
        $argsAres += "--baixar-tudo"
    }
    Invoke-Carga $argsAres
}

# ---------------------------------------------------------------------------
# DOU / ANA (via XML DOU): origem=dou no projeto — precisa URL base oficial
# Formato esperado pelo script: .../arquivos/{ano}/{mes}/S01{mes}{ano}.zip etc.
# Documentação: https://www.gov.br/inpi/pt-br/assuntos/diario-oficial (ajuste conforme URL atual)
# ---------------------------------------------------------------------------
if ($doDou) {
    if ([string]::IsNullOrWhiteSpace($DouBaseUrl)) {
        Write-Host "`n=== DOU (coletar_dou_base) ===" -ForegroundColor Green
        Write-Host "AVISO: DouBaseUrl vazio. Pule esta parte ou execute:" -ForegroundColor Yellow
        Write-Host '  .\setup\carga_normas_azure.ps1 -SoDou -DouBaseUrl "https://URL_BASE_DO_REPOSITORIO_DOU"' -ForegroundColor Gray
        Write-Host "Exemplo de chamada manual:" -ForegroundColor Gray
        Write-Host "  python -m scripts.coletar_dou_base --ano 2024 --mes 1 --base-url `"https://...`"" -ForegroundColor Gray
    }
    else {
        Write-Host "`n=== DOU (coletar_dou_base) ano $AnoInicio..$AnoFim ===" -ForegroundColor Green
        for ($a = $AnoInicio; $a -le $AnoFim; $a++) {
            foreach ($m in $Meses) {
                Write-Host "-- Ano $a mes $m --" -ForegroundColor Cyan
                try {
                    Invoke-Carga @("-m", "scripts.coletar_dou_base", "--ano", "$a", "--mes", "$m", "--base-url", $DouBaseUrl)
                }
                catch {
                    Write-Host "  (aviso) Falhou $a/$m : $_" -ForegroundColor DarkYellow
                }
            }
        }
    }
}

# ---------------------------------------------------------------------------
# ANA — resoluções regulatórias (gov.br), origem=govbr
# ---------------------------------------------------------------------------
if ($doAnaGovbr) {
    Write-Host "`n=== ANA gov.br (coletar_ana_govbr) ===" -ForegroundColor Green
    $argsAna = @("-m", "scripts.coletar_ana_govbr")
    if ($LimiteAnaGovbr -gt 0) {
        $argsAna += "--limite", "$LimiteAnaGovbr"
    }
    Invoke-Carga $argsAna
}

Write-Host "`nConcluído. Verifique no Azure:" -ForegroundColor Green
Write-Host "  https://<seu-site>.azurewebsites.net/api/public/atos?limit=50&offset=0" -ForegroundColor Gray
Write-Host "O campo 'total' deve aumentar após a carga." -ForegroundColor Gray
