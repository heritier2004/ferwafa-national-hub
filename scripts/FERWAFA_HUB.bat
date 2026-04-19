@echo off
title FERWAFA National Intelligence Hub
echo Starting FERWAFA National Intelligence Hub...
echo.
cd /d "c:\Users\User\Documents\NEW_VERSION"
echo [1/2] Launching Backend API...
start "FERWAFA_BACKEND" cmd /k "python -m backend.app.main"
echo [2/2] Opening Dashboard in Browser...
timeout /t 3 /nobreak > nul
start http://localhost:8001
echo.
echo ===================================================
echo HUB IS ONLINE: http://localhost:8001
echo ===================================================
pause
