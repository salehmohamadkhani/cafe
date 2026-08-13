@echo off
setlocal
chcp 65001 >nul
title Cafe Platform - One Click Setup and Run

echo ============================================================
echo        Cafe Platform - نصب و اجرای خودکار ویندوز
echo ============================================================
echo.

set "SETUP_SCRIPT=%~dp0scripts\windows_setup.ps1"
if not exist "%SETUP_SCRIPT%" (
    echo [خطا] فایل scripts\windows_setup.ps1 پیدا نشد.
    echo این فایل BAT باید داخل پوشه کامل پروژه باقی بماند.
    echo لطفاً کل پروژه را از GitHub دانلود و از ZIP خارج کنید.
    echo.
    pause
    exit /b 1
)

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%SETUP_SCRIPT%"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%EXIT_CODE%"=="0" (
    echo اجرای نصب‌کننده با خطا متوقف شد. پیام بالاتر را بررسی کنید.
) else (
    echo سرور متوقف شد.
)
echo این پنجره خودکار بسته نمی‌شود.
pause
exit /b %EXIT_CODE%
