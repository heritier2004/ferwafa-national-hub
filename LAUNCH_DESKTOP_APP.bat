@echo off
setlocal enabledelayedexpansion

:: Set elite terminal color (Cyan on Black)
color 0B
mode con cols=75 lines=20
title FERWAFA Intelligence Hub - Desktop Launcher

echo.
echo    ================================================================
echo    ███████╗███████╗██████╗ ██╗    ██╗ █████╗ ███████╗ █████╗ 
echo    ██╔════╝██╔════╝██╔══██╗██║    ██║██╔══██╗██╔════╝██╔══██╗
echo    █████╗  █████╗  ██████╔╝██║ █╗ ██║███████║█████╗  ███████║
echo    ██╔══╝  ██╔══╝  ██╔══██╗██║███╗██║██╔══██║██╔══╝  ██╔══██║
echo    ██║     ███████╗██║  ██║╚███╔███╔╝██║  ██║██║     ██║  ██║
echo    ╚═╝     ╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝
echo.
echo              [ NATIONAL FOOTBALL INTELLIGENCE HUB ]
echo                  NATIVE DESKTOP APP LAUNCHER
echo    ================================================================
echo.

echo  [*] Verifying Node.js and Electron environment...
call npm --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo  [!] CRITICAL: Node.js/NPM is not found in PATH.
    echo  [!] Please install Node.js to run the Desktop Application.
    pause
    exit /b
)

echo  [*] Launching Sportexa Native Desktop Application...
echo      (This will automatically start the backend and AI engine in the background)
echo.

:: Start the electron application
call npm start

echo.
echo  [*] Application Closed.
pause >nul
