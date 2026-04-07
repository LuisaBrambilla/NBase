# Empacota data/html_conteudo num ZIP em C:\Temp e mostra o caminho.
# Executar no PowerShell:
#   powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\empacotar_data_html_para_azure.ps1"

$ErrorActionPreference = "Stop"

$proj = "C:\Users\Developer\OneDrive - TECBIS\Documentos\Tecbis - Gtec\Projetos Desenvolvimento\Gen360"
$origem = Join-Path $proj "data\html_conteudo"
$tmp = "C:\Temp\deploy-data"
$zip = "C:\Temp\data-parte-html.zip"

if (-not (Test-Path $origem)) {
    Write-Host "ERRO: Pasta nao encontrada: $origem" -ForegroundColor Red
    exit 1
}

Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path (Join-Path $tmp "data\html_conteudo") -Force | Out-Null

Copy-Item -Path (Join-Path $origem "*") -Destination (Join-Path $tmp "data\html_conteudo") -Recurse -Force

if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path (Join-Path $tmp "data") -DestinationPath $zip -Force

$f = Get-Item $zip
Write-Host "ZIP criado:" -ForegroundColor Green
Write-Host $f.FullName
Write-Host ("Tamanho: {0:N2} MB" -f ($f.Length / 1MB))
Write-Host ""
Write-Host "Deploy (ajuste RG/nome se precisar):" -ForegroundColor Cyan
Write-Host ('az webapp deploy --resource-group DemoGoverno --name Gen360 --src-path "{0}" --type zip' -f $zip)
