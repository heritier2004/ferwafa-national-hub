#!/bin/bash
echo "==================================================="
echo "  ⚡  AI PITCH MACHINE  -  UNIX/MAC LAUNCHER"
echo "==================================================="
echo ""

# 1. Check for Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is required but not found."
    exit 1
fi

# 2. Setup Virtual Environment
if [ ! -d ".venv" ]; then
    echo "[INFO] Creating Virtual Environment..."
    python3 -m venv .venv
    echo "[INFO] Installing dependencies..."
    .venv/bin/python3 -m pip install --upgrade pip
    .venv/bin/python3 -m pip install -r requirements.txt
fi

# 3. Run Application
echo "[INFO] Starting AI Pitch Machine..."
.venv/bin/python3 setup_wizard.py
.venv/bin/python3 main.py
