@echo off
title FERWAFA Unified Launcher
color 0A

rem ==== Project root ==== 
set "PROJ_DIR=C:\Users\User\Documents\NEW_VERSION"
cd /d "%PROJ_DIR%"

rem ==== Ensure virtual environment exists ==== 
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

rem ==== Activate virtual environment ==== 
call .venv\Scripts\activate

rem ==== Define python executable ==== 
set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"

rem ==== Start National Hub (backend) ==== 
start "FERWAFA Hub" cmd /k "%PYTHON_EXE% -m backend.app.main"

rem ==== Start AI Pitch Machine ==== 
start "AI Pitch Machine" cmd /k "%PYTHON_EXE% -m ai_machine.main"

echo All services launched. Opening browsers in 5 seconds...
timeout /t 5 >nul
start "" "http://localhost:8001"
start "" "http://localhost:7777"

pause
