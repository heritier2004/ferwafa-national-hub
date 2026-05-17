@echo off
title AI Pitch Machine - Edge Processor
echo Starting AI Pitch Machine Edge Client...
echo.
cd /d "c:\Users\User\Documents\NEW_VERSION"
echo [1/2] Launching AI Analysis Engine...
start "AI_PITCH_MACHINE" cmd /k "python -m ai_machine.main"
echo [2/2] Opening AI Control Panel...
timeout /t 5 /nobreak > nul
start http://localhost:7777
echo.
echo ===================================================
echo AI UI IS ONLINE: http://localhost:7777
echo ===================================================
pause
