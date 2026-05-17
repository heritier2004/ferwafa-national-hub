#!/bin/bash

echo "=================================================="
echo "  FERWAFA National Football Intelligence Hub"
echo "       AI PITCH MACHINE - INSTALLER (UNIX)"
echo "=================================================="

# 1. Check for Python
if ! command -v python3 &> /dev/null
then
    echo "[ERROR] Python 3 not found. Please install Python 3.10+."
    exit 1
fi

# 2. Create Virtual Environment
if [ ! -d ".venv" ]; then
    echo "[*] Creating isolated intelligence environment..."
    python3 -m venv .venv
fi

# 3. Load Environment & Install Requirements
source .venv/bin/activate
echo "[*] Synchronizing AI dependencies..."
python3 -m pip install --upgrade pip
pip install torch torchvision torchaudio psutil ultralytics opencv-python easyocr requests psutil

# 4. Run Hardware Diagnostic
echo "[*] Running Hardware Authorization..."
python3 check_hardware.py

# 5. Launch Setup Wizard
echo "[*] Launching Intelligence Configuration..."
python3 setup_wizard.py

echo "=================================================="
echo "  INSTALLATION COMPLETE. APP IS READY."
echo "=================================================="
chmod +x start_mac_linux.sh
