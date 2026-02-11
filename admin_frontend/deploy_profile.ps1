# Envia a pagina de perfil para o servidor e verifica se subiu
$REMOTE = "root@187.77.32.179"
$PORT = "22"
$REMOTE_DIR = "/opt/resolucoes_ana/admin_frontend"

$files = @(
    "admin_profile.html",
    "admin_profile.js"
)

Write-Host "Enviando arquivos para ${REMOTE}:${REMOTE_DIR} ..." -ForegroundColor Cyan
$base = "C:\Users\Luísa\Documents\resolucoes_ana\admin_frontend"
foreach ($f in $files) {
    $local = Join-Path $base $f
    if (Test-Path $local) {
        scp -P $PORT $local "${REMOTE}:${REMOTE_DIR}/$f"
        if ($LASTEXITCODE -eq 0) { Write-Host "  OK $f" -ForegroundColor Green } else { Write-Host "  ERRO $f" -ForegroundColor Red }
    }
}

Write-Host "`nVerificando no servidor (versao nova tem 'profile-cards', antiga tem 'Em construcao')..." -ForegroundColor Cyan
ssh -P $PORT $REMOTE "grep -E 'profile-cards|Em construção' ${REMOTE_DIR}/admin_profile.html || true"
Write-Host "`nSe apareceu 'profile-cards' acima = arquivo novo. Se apareceu 'Em construção' = arquivo antigo ainda." -ForegroundColor Yellow
Write-Host "Depois abra a pagina com Ctrl+F5 (atualizacao forçada) no navegador." -ForegroundColor Yellow
