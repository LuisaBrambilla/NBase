#!/bin/bash
# Deploy na VPS: git pull, restart da API e registo no audit_log.
# Uso: ./scripts/deploy_vps.sh
#       ./scripts/deploy_vps.sh --nota "Descrição do deploy"
#
# Na VPS, na primeira vez: chmod +x scripts/deploy_vps.sh
# Opcional: definir PROJECT_DIR e SERVICE_NAME se forem diferentes.

set -e
PROJECT_DIR="${PROJECT_DIR:-/opt/resolucoes_ana}"
SERVICE_NAME="${SERVICE_NAME:-ana-api}"

cd "$PROJECT_DIR"
echo ">>> Git pull em $(pwd)"
git pull

if command -v systemctl >/dev/null 2>&1 && [ -n "$SERVICE_NAME" ]; then
  echo ">>> Reiniciar serviço: $SERVICE_NAME"
  sudo systemctl restart "$SERVICE_NAME"
fi

echo ">>> Registar deploy no audit_log"
. venv/bin/activate
python scripts/registrar_deploy.py "$@"
echo ">>> Deploy concluído."
