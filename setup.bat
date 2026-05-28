@echo off
echo ===================================================
echo   ChefCompanion Local Setup Script (Windows)
echo ===================================================
echo.

if not exist ".env" (
    echo [1/5] Creating .env from .env.example...
    copy .env.example .env
) else (
    echo [1/5] .env already exists. Skipping...
)

echo.
echo [2/5] Creating Python virtual environment...
python -m venv venv
if %ERRORLEVEL% neq 0 (
    echo Failed to create virtual environment.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [3/5] Installing backend dependencies...
call .\venv\Scripts\activate.bat
pip install -r backend\requirements.txt
if %ERRORLEVEL% neq 0 (
    echo Failed to install Python dependencies.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [4/5] Seeding database...
set PYTHONPATH=backend
python backend\seed.py
if %ERRORLEVEL% neq 0 (
    echo Failed to seed database.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [5/5] Installing frontend dependencies...
cd frontend
call npm install
if %ERRORLEVEL% neq 0 (
    echo Failed to install npm dependencies.
    cd ..
    pause
    exit /b %ERRORLEVEL%
)
cd ..

echo.
echo ===================================================
echo   Setup Complete!
echo   You can now run the app using: start.bat
echo ===================================================
echo.
pause
