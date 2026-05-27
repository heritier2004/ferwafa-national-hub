@echo off
setlocal
rem Change to the directory of this script
cd /d "%~dp0"

rem Ensure virtual environment exists
if not exist ".venv" (
    echo Virtual environment not found, creating... 
    python -m venv .venv
)

rem Activate the virtual environment
call .venv\Scripts\activate.bat

rem Start the AI Pitch Machine (FastAPI + GUI)
python main.py
