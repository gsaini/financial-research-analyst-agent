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

# Default ports
API_PORT="${API_PORT:-8000}"
STREAMLIT_PORT="${STREAMLIT_PORT:-8501}"

echo "Starting Financial Research Analyst Platform..."
echo ""
echo "  API Server:          http://localhost:${API_PORT}"
echo "  API Docs:            http://localhost:${API_PORT}/docs"
echo "  Streamlit Dashboard: http://localhost:${STREAMLIT_PORT}"
echo ""

# Cleanup background processes on exit
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $API_PID $STREAMLIT_PID 2>/dev/null
    wait $API_PID $STREAMLIT_PID 2>/dev/null
    echo "Done."
}
trap cleanup EXIT INT TERM

# Start API server in background
python -m src.main api &
API_PID=$!

# Start Streamlit dashboard in background
streamlit run frontend/app.py \
    --server.port "$STREAMLIT_PORT" \
    --server.headless true \
    --browser.gatherUsageStats false &
STREAMLIT_PID=$!

# Wait for either process to exit
wait -n $API_PID $STREAMLIT_PID 2>/dev/null || true
