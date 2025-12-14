# اسکریپت PowerShell برای deployment پروژه کافه به سرور
# استفاده: .\deploy.ps1

$ErrorActionPreference = "Stop"

Write-Host "🚀 شروع deployment پروژه کافه..." -ForegroundColor Green

# تنظیمات
$SERVER_IP = $env:CAFE_SERVER_IP
$SERVER_USER = $env:CAFE_SERVER_USER
$SERVER_PASSWORD = $env:CAFE_SERVER_PASSWORD
$PROJECT_NAME = "کافه"
$REMOTE_PATH = "/var/www/$PROJECT_NAME"
$LOCAL_PATH = $PSScriptRoot

if (-not $SERVER_IP) { throw "CAFE_SERVER_IP را در Environment Variables تنظیم کنید." }
if (-not $SERVER_USER) { $SERVER_USER = "root" }
if (-not $SERVER_PASSWORD) { Write-Host "⚠️  CAFE_SERVER_PASSWORD تنظیم نشده است. برای WinSCP دستی وارد کنید." -ForegroundColor Yellow }

# بررسی وجود OpenSSH
Write-Host "`n📦 بررسی ابزارهای لازم..." -ForegroundColor Yellow
try {
    $sshVersion = ssh -V 2>&1
    Write-Host "✅ OpenSSH موجود است" -ForegroundColor Green
} catch {
    Write-Host "❌ OpenSSH نصب نیست. لطفاً نصب کنید:" -ForegroundColor Red
    Write-Host "Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0" -ForegroundColor Yellow
    exit 1
}

# بررسی وجود sshpass یا استفاده از روش جایگزین
Write-Host "`n📁 ایجاد پوشه در سرور..." -ForegroundColor Yellow
$sshCommand = "mkdir -p $REMOTE_PATH"
try {
    # استفاده از Plink یا sshpass (اگر نصب است)
    # در غیر این صورت، دستورات را به صورت دستی اجرا کنید
    Write-Host "⚠️  لطفاً به صورت دستی به سرور متصل شوید و دستورات زیر را اجرا کنید:" -ForegroundColor Yellow
    Write-Host "ssh $SERVER_USER@$SERVER_IP" -ForegroundColor Cyan
    Write-Host "mkdir -p $REMOTE_PATH" -ForegroundColor Cyan
} catch {
    Write-Host "❌ خطا در اتصال به سرور" -ForegroundColor Red
}

# لیست فایل‌های لازم برای کپی
Write-Host "`n📋 فایل‌های لازم برای کپی:" -ForegroundColor Yellow
$filesToCopy = @(
    "app.py",
    "auth.py",
    "config.py",
    "wsgi.py",
    "requirements_production.txt",
    "gunicorn_config.py",
    "nginx_config.conf",
    "systemd_service.txt",
    "templates",
    "static",
    "models",
    "routes",
    "services",
    "utils",
    "migrations"
)

foreach ($file in $filesToCopy) {
    if (Test-Path "$LOCAL_PATH\$file") {
        Write-Host "  ✅ $file" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  $file (یافت نشد)" -ForegroundColor Yellow
    }
}

# دستورات SCP
Write-Host "`n📤 دستورات کپی فایل‌ها:" -ForegroundColor Yellow
Write-Host "لطفاً از یکی از روش‌های زیر استفاده کنید:" -ForegroundColor Cyan
Write-Host ""
Write-Host "روش 1: استفاده از WinSCP (توصیه می‌شود)" -ForegroundColor Green
Write-Host "  1. دانلود WinSCP از https://winscp.net" -ForegroundColor White
Write-Host "  2. اتصال با اطلاعات زیر:" -ForegroundColor White
Write-Host "     Host: $SERVER_IP" -ForegroundColor Cyan
Write-Host "     User: $SERVER_USER" -ForegroundColor Cyan
Write-Host "     Password: (از ENV/ورودی دستی)" -ForegroundColor Cyan
Write-Host "  3. کپی تمام فایل‌ها به $REMOTE_PATH" -ForegroundColor White
Write-Host ""
Write-Host "روش 2: استفاده از PowerShell SCP" -ForegroundColor Green
Write-Host "  scp -r $LOCAL_PATH\* $SERVER_USER@${SERVER_IP}:$REMOTE_PATH/" -ForegroundColor Cyan
Write-Host ""

# نمایش دستورات بعدی
Write-Host "`n📝 بعد از کپی فایل‌ها، دستورات زیر را در سرور اجرا کنید:" -ForegroundColor Yellow
Write-Host "  ssh $SERVER_USER@$SERVER_IP" -ForegroundColor Cyan
Write-Host "  cd $REMOTE_PATH" -ForegroundColor Cyan
Write-Host "  bash <(cat << 'EOF'" -ForegroundColor Cyan
Write-Host "  apt update" -ForegroundColor White
Write-Host "  apt install -y python3 python3-pip python3-venv nginx" -ForegroundColor White
Write-Host "  python3 -m venv venv" -ForegroundColor White
Write-Host "  source venv/bin/activate" -ForegroundColor White
Write-Host "  pip install --upgrade pip" -ForegroundColor White
Write-Host "  pip install -r requirements_production.txt" -ForegroundColor White
Write-Host "  pip install gunicorn" -ForegroundColor White
Write-Host "  mkdir -p instance /var/log/cafe" -ForegroundColor White
Write-Host "  chmod 755 /var/log/cafe" -ForegroundColor White
Write-Host "  EOF" -ForegroundColor Cyan
Write-Host ""

Write-Host "✅ دستورالعمل‌های کامل در فایل DEPLOYMENT.md موجود است" -ForegroundColor Green

