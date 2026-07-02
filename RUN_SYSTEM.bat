@echo off
title FERWAFA Unified Runner
color 0A

rem ==== Project root ==== 
set "PROJ_DIR=%~dp0"
cd /d "%PROJ_DIR%"

echo Starting National Football Intelligence System...
echo --------------------------------------------------

rem ==== Define python executable ==== 
if exist ".venv\Scripts\python.exe" (
    echo [INFO] Virtual environment detected. Using local python.
    set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
) else (
    echo [WARN] Virtual environment .venv not found. Using system python.
    set "PYTHON_EXE=python"
)

echo [1/1] Starting Backend API and Frontend Hub (Port 8001)...
start "FERWAFA HUB" cmd /k "%PYTHON_EXE% -m backend.app.main"

echo.
echo --------------------------------------------------
echo SYSTEM IS STARTING!
echo Please wait 5 seconds and then open this link in your browser:
echo http://localhost:8001
echo --------------------------------------------------
echo.
pause
