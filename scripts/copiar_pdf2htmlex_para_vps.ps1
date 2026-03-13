# Copia lib/pdf2htmlex.py e scripts/converter_pdf_para_html_arespcj.py para a VPS.
# Uso (PowerShell, na pasta raiz do projeto):
#   $env:VPS_HOST = "root@187.77.32.179"   # ou o teu user@host
#   .\scripts\copiar_pdf2htmlex_para_vps.ps1
# Ou em uma linha (ajusta o host):
#   $vps = "root@187.77.32.179"; scp lib/pdf2htmlex.py "$vps`:/opt/resolucoes_ana/lib/"; scp scripts/converter_pdf_para_html_arespcj.py "$vps`:/opt/resolucoes_ana/scripts/"

$ErrorActionPreference = "Stop"
$vps = $env:VPS_HOST
if (-not $vps) {
    $vps = "root@187.77.32.179"
    Write-Host "A usar VPS_HOST = $vps (define `$env:VPS_HOST para alterar)"
}
$raiz = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $raiz
$dest = "${vps}:/opt/resolucoes_ana"
Write-Host "A copiar para $dest ..."
scp lib/pdf2htmlex.py "${dest}/lib/"
scp scripts/converter_pdf_para_html_arespcj.py "${dest}/scripts/"
Write-Host "Concluído. Na VPS execute: cd /opt/resolucoes_ana && source venv/bin/activate && python scripts/converter_pdf_para_html_arespcj.py --limit 2"
