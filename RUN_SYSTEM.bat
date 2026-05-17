@echo off
echo Starting National Football Intelligence System...
echo --------------------------------------------------

echo [1/1] Starting Backend API & Frontend Hub (Port 8001)...
start "FERWAFA HUB" cmd /k "python -m backend.app.main"

echo.
echo --------------------------------------------------
echo SYSTEM IS STARTING!
echo Please wait 5 seconds and then open this link in your browser:
echo http://localhost:8001
echo --------------------------------------------------
echo.
pause
