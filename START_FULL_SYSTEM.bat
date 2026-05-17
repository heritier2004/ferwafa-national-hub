@echo off
title FERWAFA Unified Intelligence Launcher
echo [0/2] INITIALIZING NATIONAL LEDGER (Database)...
powershell -ExecutionPolicy Bypass -File START_DB.ps1

echo.
echo [1/2] STARTING NATIONAL INTELLIGENCE HUB (Port 8001)...
echo ===================================================
start "FERWAFA_HUB" cmd /k "python -m backend.app.main"

timeout /t 5 /nobreak > nul

echo.
echo ===================================================
echo [2/2] STARTING AI PITCH MACHINE (Edge Processor)...
echo ===================================================
start "AI_PITCH_MACHINE" cmd /k "python -m ai_machine.main"

echo.
echo --------------------------------------------------
echo ALL SYSTEMS ARE STARTING!
echo --------------------------------------------------
echo - Hub Dashboard:  http://localhost:8001
echo - AI Control:     http://localhost:7777
echo --------------------------------------------------
echo.
pause
