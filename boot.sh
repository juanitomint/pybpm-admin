#!/usr/bin/env bash
set -euo pipefail

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Start the application
echo "Starting the application..."
exec uv run uvicorn main:app --host 0.0.0.0 --port ${APP_PORT:-5000} ${APP_EXTRA:""}
