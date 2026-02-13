#!/bin/bash
# Azure App Service startup script for FastAPI

# Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# Start the application with Gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker api.main:app --bind=0.0.0.0:8000 --timeout 600
