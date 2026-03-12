#!/bin/bash
# Startup para Azure App Service (Linux).
# A Azure define a variável PORT; o working directory é a raiz do projeto.
cd "$(dirname "$0")"
export PORT="${PORT:-8000}"
exec python -m uvicorn api.main:root_app --host 0.0.0.0 --port "$PORT"
