#!/bin/bash
echo "==================================================="
echo "  AI Pitch Machine (Edge Client) - Mac/Linux Start"
echo "==================================================="
echo ""
echo "Installing dependencies (if needed)..."
python3 -m pip install -r requirements.txt > /dev/null 2>&1 || python -m pip install -r requirements.txt > /dev/null 2>&1

echo "Starting Setup Wizard..."
python3 setup_wizard.py || python setup_wizard.py
