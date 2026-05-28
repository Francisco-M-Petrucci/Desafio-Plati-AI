#!/bin/bash
echo "==================================================="
echo "  ChefCompanion Local Setup Script (Mac/Linux)"
echo "==================================================="
echo ""

if [ ! -f .env ]; then
    echo "[1/5] Creating .env from .env.example..."
    cp .env.example .env
else
    echo "[1/5] .env already exists. Skipping..."
fi

echo ""
echo "[2/5] Creating Python virtual environment..."
python3 -m venv venv || { echo "Failed to create virtual environment."; exit 1; }

echo ""
echo "[3/5] Installing backend dependencies..."
source venv/bin/activate
pip install -r backend/requirements.txt || { echo "Failed to install Python dependencies."; exit 1; }

echo ""
echo "[4/5] Seeding database..."
export PYTHONPATH=backend
python3 backend/seed.py || { echo "Failed to seed database."; exit 1; }

echo ""
echo "[5/5] Installing frontend dependencies..."
cd frontend
npm install || { echo "Failed to install npm dependencies."; exit 1; }
cd ..

echo ""
echo "==================================================="
echo "  Setup Complete!"
echo "  You can now run the app using: ./start.sh"
echo "==================================================="
echo ""
