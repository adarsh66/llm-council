#!/bin/sh
# -----------------------------------------------------------------------------
# startup.sh
# Custom startup script for Azure App Service to ensure dependencies and start the app
# -----------------------------------------------------------------------------

# Navigate to the app root
cd /home/site/wwwroot || exit

echo "[startup.sh] Checking dependencies..."

# Check if uvicorn is importable; if not, install requirements
if ! python -c "import uvicorn" 2>/dev/null; then
    echo "[startup.sh] 'uvicorn' module not found. Installing dependencies from requirements.txt..."
    pip install --upgrade pip
    pip install -r requirements.txt
else
    echo "[startup.sh] Dependencies seem present."
fi

# Set default Environment variables if missing
export DATA_DIR="${DATA_DIR:-/home/data/conversations}"

# Ensure data directory exists
mkdir -p "$DATA_DIR"

echo "[startup.sh] Starting Gunicorn with Uvicorn worker..."
# Use python -m gunicorn to ensure we use the installed module
exec python -m gunicorn backend.main:app \
    --bind 0.0.0.0:$PORT \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 180 \
    --access-logfile - \
    --error-logfile -
