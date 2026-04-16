#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/hr-ai-platform"
FRONTEND="$ROOT/frontend"

cleanup() {
    echo ""
    echo "Shutting down..."
    [[ -n "$BACKEND_PID" ]] && kill "$BACKEND_PID" 2>/dev/null
    [[ -n "$FRONTEND_PID" ]] && kill "$FRONTEND_PID" 2>/dev/null
    wait 2>/dev/null
    echo "All servers stopped."
}
trap cleanup EXIT INT TERM

# --- Backend (FastAPI + Uvicorn) ---
echo "Starting backend on http://localhost:8000 ..."
cd "$BACKEND"
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# --- Frontend (Vite) ---
echo "Starting frontend on http://localhost:5173 ..."
cd "$FRONTEND"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "====================================="
echo "  Backend  → http://localhost:8000"
echo "  Frontend → http://localhost:5173"
echo "  Press Ctrl+C to stop both"
echo "====================================="

wait
