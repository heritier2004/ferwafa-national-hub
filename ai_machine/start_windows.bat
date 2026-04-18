@echo off
echo ===================================================
echo   AI Pitch Machine (Edge Client) - Windows Start
echo ===================================================
echo.
echo Installing dependencies (if needed)...
python -m pip install -r requirements.txt > nul 2>&1

echo Starting Setup Wizard...
python setup_wizard.py
pause
