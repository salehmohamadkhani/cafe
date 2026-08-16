@echo off
setlocal
title Cafe Platform - One Click Setup and Run

echo ============================================================
echo        Cafe Platform - One Click Windows Setup and Run
echo ============================================================
echo.

set "SETUP_SCRIPT=%~dp0scripts\windows_setup.ps1"
if not exist "%SETUP_SCRIPT%" (
    echo [ERROR] scripts\windows_setup.ps1 was not found.
    echo This BAT file must stay inside the full project folder.
    echo Please download the whole project from GitHub and extract it from the ZIP.
    echo.
    pause
    exit /b 1
)

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%SETUP_SCRIPT%"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%EXIT_CODE%"=="0" (
    echo Setup stopped with an error. Check the message above.
) else (
    echo Server stopped.
)
echo This window does not close automatically.
pause
exit /b %EXIT_CODE%
