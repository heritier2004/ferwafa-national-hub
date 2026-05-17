@echo off
setlocal enabledelayedexpansion

:: Set elite terminal color (Cyan on Black)
color 0B
mode con cols=90 lines=30
title FERWAFA Intelligence Hub - AI Machine Installer

echo.
echo    ========================================================================
echo    ███████╗███████╗██████╗ ██╗    ██╗ █████╗ ███████╗ █████╗ 
echo    ██╔════╝██╔════╝██╔══██╗██║    ██║██╔══██╗██╔════╝██╔══██╗
echo    █████╗  █████╗  ██████╔╝██║ █╗ ██║███████║█████╗  ███████║
echo    ██╔══╝  ██╔══╝  ██╔══██╗██║███╗██║██╔══██║██╔══╝  ██╔══██║
echo    ██║     ███████╗██║  ██║╚███╔███╔╝██║  ██║██║     ██║  ██║
echo    ╚═╝     ╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝
echo.
echo                [ NATIONAL FOOTBALL INTELLIGENCE HUB ]
echo                  AI PITCH MACHINE - SETUP UTILITY
echo    ========================================================================
echo.

:: 1. Check for Python
echo  [*] Verifying system environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo  [!] CRITICAL: Python 3.10+ is required but not found in PATH.
    echo  [!] Please install Python and ensure "Add to PATH" is checked.
    pause
    exit /b
)
echo      - Python Environment: OK
echo.

:: 2. Create Virtual Environment
if not exist .venv (
    echo  [*] Generating isolated intelligence environment...
    python -m venv .venv
    echo      - Virtual Environment: CREATED
) else (
    echo  [*] Intelligence environment verified.
)
echo.

:: 3. Update Pip & Install Core Requirements
echo  [*] Synchronizing AI neural network dependencies...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul 2>&1
echo      - Package Manager: UP-TO-DATE
echo      - Downloading PyTorch, YOLOv8, OpenCV, EasyOCR...
pip install torch torchvision torchaudio psutil ultralytics opencv-python easyocr requests winshell pypiwin32 >nul 2>&1
echo      - AI Modules: INSTALLED
echo.

:: 4. Run Hardware Diagnostic
echo  [*] Running Hardware Authorization Diagnostic...
python check_hardware.py
echo.

:: 5. Create Desktop Shortcut
echo  [*] Generating Mission Control Launcher...
python create_desktop_icon.py
echo      - Desktop Shortcut: CREATED
echo.

:: 6. Launch Setup Wizard
echo  [*] Launching AI Intelligence Configuration...
timeout /t 2 /nobreak >nul
python setup_wizard.py

echo.
echo    ========================================================================
echo      INSTALLATION COMPLETE. THE SYSTEM IS READY.
echo      You may now close this window and use the Desktop icon.
echo    ========================================================================
pause >nul
