#!/usr/bin/env bash
# PDF Toolkit - Linux/macOS launcher
# Usage:  bash start.sh   (or ./start.sh after chmod +x)
set -e
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "[INFO] Creating virtual environment..."
    python3 -m venv venv
fi

# shellcheck disable=SC1091
source venv/bin/activate

echo "[INFO] Installing dependencies (first run takes a minute)..."
python -m pip install -r requirements.txt

echo "[OK] Starting PDF Toolkit at http://127.0.0.1:8010"
python backend/main.py
