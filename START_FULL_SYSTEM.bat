@echo off
title FERWAFA Unified Launcher
color 0A

rem ==== Project root ==== 
set "PROJ_DIR=%~dp0"
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

rem ==== Install required Python packages if missing ==== 
%PYTHON_EXE% -m pip install --quiet uvicorn fastapi

rem ==== Start National Hub (backend) ==== 
start "FERWAFA Hub" cmd /k "%PYTHON_EXE% -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8001 --reload"

rem ==== Start AI Pitch Machine ==== 
start "AI Pitch Machine" cmd /k "%PYTHON_EXE% -m ai_machine.main"

echo All services launched. Waiting for backend to become healthy...
rem Wait up to 30 seconds, checking /health every 5 seconds
set "MAX_WAIT=30"
set "WAITED=0"
:check_health
timeout /t 5 >nul
powershell -Command "try { $r = Invoke-WebRequest -Uri http://localhost:8001/health -UseBasicParsing; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"
if %errorlevel%==0 (
    echo Backend is healthy. Opening UI...
    start "" "http://localhost:8001"
) else (
    set /a WAITED+=5
    if %WAITED% geq %MAX_WAIT% (
        echo Backend did not become healthy after %MAX_WAIT% seconds. Opening anyway.
        start "" "http://localhost:8001"
    ) else (
        goto :check_health
    )
)

pause
