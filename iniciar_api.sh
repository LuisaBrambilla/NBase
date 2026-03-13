#!/bin/bash
# Inicia a API em modo desenvolvimento (Linux/macOS).
# Uso: ./iniciar_api.sh
# Para produção em segundo plano: nohup uvicorn api.main:root_app --host 0.0.0.0 --port 8000 > uvicorn.log 2>&1 &

set -e
cd "$(dirname "$0")"

# Ativa o venv se existir
if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
    echo "A ativar ambiente virtual..."
    source venv/bin/activate
fi

echo "A iniciar API (uvicorn com --reload). Pressione Ctrl+C para parar."
exec python -m uvicorn api.main:root_app --reload --host 0.0.0.0 --port 8000
