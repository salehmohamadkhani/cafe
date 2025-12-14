# اسکریپت ساده برای آپلود با SCP
$SERVER_IP = $env:CAFE_SERVER_IP
$SERVER_USER = $env:CAFE_SERVER_USER
$SERVER_PASSWORD = $env:CAFE_SERVER_PASSWORD
$REMOTE_PATH = $env:CAFE_REMOTE_PATH
$LOCAL_PATH = Get-Location

Write-Host "🚀 شروع آپلود فایل‌ها..." -ForegroundColor Green

if (-not $SERVER_IP) { throw "CAFE_SERVER_IP را در Environment Variables تنظیم کنید." }
if (-not $SERVER_USER) { $SERVER_USER = "root" }
if (-not $SERVER_PASSWORD) { throw "CAFE_SERVER_PASSWORD را در Environment Variables تنظیم کنید." }
if (-not $REMOTE_PATH) { $REMOTE_PATH = "/var/www/کافه" }

# ایجاد پوشه در سرور
Write-Host "📁 ایجاد پوشه در سرور..." -ForegroundColor Yellow
$createFolder = "echo $SERVER_PASSWORD | ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP `"mkdir -p $REMOTE_PATH`""
Invoke-Expression $createFolder

# کپی فایل‌ها با SCP
Write-Host "📤 کپی فایل‌ها..." -ForegroundColor Yellow

# فایل‌های اصلی
$files = @("app.py", "auth.py", "config.py", "wsgi.py", "requirements_production.txt", "gunicorn_config.py", "nginx_config.conf", "systemd_service.txt", "deploy_remote.sh")

foreach ($file in $files) {
    if (Test-Path $file) {
        Write-Host "  📄 $file..." -ForegroundColor Cyan
        $scpCmd = "scp -o StrictHostKeyChecking=no $file ${SERVER_USER}@${SERVER_IP}:${REMOTE_PATH}/"
        & cmd /c "echo $SERVER_PASSWORD | $scpCmd"
    }
}

# کپی پوشه‌ها
$folders = @("templates", "static", "models", "routes", "services", "utils", "migrations")

foreach ($folder in $folders) {
    if (Test-Path $folder) {
        Write-Host "  📁 $folder..." -ForegroundColor Cyan
        $scpCmd = "scp -r -o StrictHostKeyChecking=no $folder ${SERVER_USER}@${SERVER_IP}:${REMOTE_PATH}/"
        & cmd /c "echo $SERVER_PASSWORD | $scpCmd"
    }
}

Write-Host "`n✅ آپلود کامل شد!" -ForegroundColor Green

