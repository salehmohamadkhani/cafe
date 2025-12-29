# راه‌اندازی پروژه Cafe Management
$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  راه‌اندازی پروژه Cafe Management" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# تغییر به پوشه اسکریپت
Set-Location $PSScriptRoot

# بررسی وجود Python
Write-Host "[*] بررسی Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[✓] Python پیدا شد: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[خطا] Python نصب نشده است!" -ForegroundColor Red
    Write-Host "لطفاً Python را از https://www.python.org دانلود و نصب کنید." -ForegroundColor Red
    Read-Host "برای خروج Enter را بزنید"
    exit 1
}

# بررسی وجود محیط مجازی
if (-not (Test-Path "venv")) {
    Write-Host ""
    Write-Host "[*] ایجاد محیط مجازی..." -ForegroundColor Yellow
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[خطا] ایجاد محیط مجازی با مشکل مواجه شد!" -ForegroundColor Red
        Read-Host "برای خروج Enter را بزنید"
        exit 1
    }
    Write-Host "[✓] محیط مجازی ایجاد شد" -ForegroundColor Green
} else {
    Write-Host "[✓] محیط مجازی موجود است" -ForegroundColor Green
}

# فعال‌سازی محیط مجازی
Write-Host ""
Write-Host "[*] فعال‌سازی محیط مجازی..." -ForegroundColor Yellow
if (Test-Path "venv\Scripts\Activate.ps1") {
    & "venv\Scripts\Activate.ps1"
} else {
    $env:VIRTUAL_ENV = "$PSScriptRoot\venv"
    $env:PATH = "$env:VIRTUAL_ENV\Scripts;$env:PATH"
}

# تنظیم Python از محیط مجازی
$pythonExe = "venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python"
}
Write-Host "[✓] استفاده از: $pythonExe" -ForegroundColor Green

# به‌روزرسانی pip
Write-Host ""
Write-Host "[*] به‌روزرسانی pip..." -ForegroundColor Yellow
& $pythonExe -m pip install --upgrade pip --quiet

# نصب وابستگی‌ها
Write-Host ""
Write-Host "[*] نصب وابستگی‌های ضروری پروژه..." -ForegroundColor Yellow
Write-Host "استفاده از requirements_minimal.txt (بدون نیاز به کامپایل)" -ForegroundColor Gray
Write-Host "این ممکن است چند دقیقه طول بکشد..." -ForegroundColor Gray
& $pythonExe -m pip install -r requirements_minimal.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[خطا] نصب وابستگی‌های ضروری با مشکل مواجه شد!" -ForegroundColor Red
    Write-Host ""
    Write-Host "[توجه] اگر می‌خواهید همه پکیج‌ها را نصب کنید:" -ForegroundColor Yellow
    Write-Host "1. Microsoft Visual C++ Build Tools را نصب کنید" -ForegroundColor Yellow
    Write-Host "   از: https://visualstudio.microsoft.com/visual-cpp-build-tools/" -ForegroundColor Yellow
    Write-Host "2. سپس دستور زیر را اجرا کنید:" -ForegroundColor Yellow
    Write-Host "   $pythonExe -m pip install -r requirements.txt" -ForegroundColor Yellow
    Read-Host "`nبرای خروج Enter را بزنید"
    exit 1
}
Write-Host "[✓] وابستگی‌های ضروری نصب شدند" -ForegroundColor Green

# تلاش برای نصب greenlet
Write-Host ""
Write-Host "[*] بررسی greenlet..." -ForegroundColor Yellow
try {
    & $pythonExe -c "import greenlet" 2>$null
    Write-Host "[✓] greenlet موجود است" -ForegroundColor Green
} catch {
    Write-Host "[*] تلاش برای نصب greenlet (فقط wheel)..." -ForegroundColor Yellow
    & $pythonExe -m pip install --only-binary :all: greenlet 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[✓] greenlet نصب شد" -ForegroundColor Green
    } else {
        Write-Host "[توجه] greenlet نصب نشد (نیاز به کامپایل)" -ForegroundColor Yellow
        Write-Host "SQLAlchemy ممکن است بدون greenlet کار کند، اما عملکرد بهتری با آن دارد." -ForegroundColor Gray
    }
}

# ایجاد پوشه instance
if (-not (Test-Path "instance")) {
    Write-Host ""
    Write-Host "[*] ایجاد پوشه instance..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path "instance" | Out-Null
    Write-Host "[✓] پوشه instance ایجاد شد" -ForegroundColor Green
}

# اجرای پروژه
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  پروژه در حال اجرا است..." -ForegroundColor Cyan
Write-Host "  آدرس: http://localhost:5000" -ForegroundColor Cyan
Write-Host "  برای توقف: Ctrl+C" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

& $pythonExe app.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "  خطا در اجرای پروژه!" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
}

Read-Host "برای خروج Enter را بزنید"

