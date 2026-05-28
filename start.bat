@echo off
echo ===================================================
echo   ChefCompanion Local Startup Script
echo ===================================================

echo.
echo Cleaning up any running servers on ports 8000 and 5173...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill /f /pid %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 ^| findstr LISTENING') do taskkill /f /pid %%a 2>nul

echo.
echo [1/2] Launching Backend Server in a new window...
start cmd /k "title ChefCompanion Backend && set PYTHONPATH=backend && .\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

echo [2/2] Launching Frontend Server in a new window...
start cmd /k "title ChefCompanion Frontend && cd frontend && npm run dev"

echo.
echo ===================================================
echo   Both servers are launching!
echo   - Backend: http://127.0.0.1:8000
echo   - Frontend: http://localhost:5173/
echo ===================================================
echo.
pause
