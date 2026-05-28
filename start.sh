#!/bin/bash
echo "==================================================="
echo "  ChefCompanion Local Startup Script (Mac/Linux)"
echo "==================================================="
echo ""

echo "Cleaning up any running servers on ports 8000 and 5173..."
# Kill process on port 8000
lsof -ti :8000 | xargs kill -9 2>/dev/null
# Kill process on port 5173
lsof -ti :5173 | xargs kill -9 2>/dev/null

echo ""
echo "[1/2] Launching Backend Server in the background..."
export PYTHONPATH=backend
source venv/bin/activate
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

echo "[2/2] Launching Frontend Server in the background..."
cd frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "==================================================="
echo "  Both servers are launching!"
echo "  - Backend: http://127.0.0.1:8000"
echo "  - Frontend: http://localhost:5173/"
echo "  Press Ctrl+C to stop both servers."
echo "==================================================="
echo ""

# Wait for any process to exit or Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
