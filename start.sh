#!/bin/bash
# Start the Financial Research Analyst API server

cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Load .env if present
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

export PYTHONWARNINGS="ignore::UserWarning"

echo "Starting Financial Research Analyst API..."
echo "Docs: http://localhost:8000/docs"
echo ""

python -m src.main api
