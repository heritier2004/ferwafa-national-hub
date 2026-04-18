@echo off
echo Starting National Football Intelligence System...
echo --------------------------------------------------

echo [1/2] Starting Backend API (Port 8001)...
start "FERWAFA BACKEND" cmd /k "python -m backend.app.main"

echo [2/2] Starting Frontend Hub (Port 8002)...
start "FERWAFA FRONTEND" cmd /k "python -m http.server 8002 --directory frontend"

echo.
echo --------------------------------------------------
echo SYSTEM IS STARTING!
echo Please wait 5 seconds and then open this link in your browser:
echo http://localhost:8002
echo --------------------------------------------------
echo.
pause
