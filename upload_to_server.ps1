# اسکریپت PowerShell برای آپلود فایل‌ها به سرور
$ErrorActionPreference = "Stop"

$SERVER_IP = $env:CAFE_SERVER_IP
$SERVER_USER = $env:CAFE_SERVER_USER
$SERVER_PASSWORD = $env:CAFE_SERVER_PASSWORD
$REMOTE_PATH = $env:CAFE_REMOTE_PATH
$LOCAL_PATH = Get-Location

Write-Host "🚀 شروع آپلود فایل‌ها به سرور..." -ForegroundColor Green

if (-not $SERVER_IP) { throw "CAFE_SERVER_IP را در Environment Variables تنظیم کنید." }
if (-not $SERVER_USER) { $SERVER_USER = "root" }
if (-not $SERVER_PASSWORD) { throw "CAFE_SERVER_PASSWORD را در Environment Variables تنظیم کنید." }
if (-not $REMOTE_PATH) { $REMOTE_PATH = "/var/www/کافه" }

# نصب ماژول Posh-SSH اگر نصب نیست
if (-not (Get-Module -ListAvailable -Name Posh-SSH)) {
    Write-Host "📦 نصب ماژول Posh-SSH..." -ForegroundColor Yellow
    Install-Module -Name Posh-SSH -Force -Scope CurrentUser -AllowClobber
}

Import-Module Posh-SSH

# ایجاد credential
$securePassword = ConvertTo-SecureString $SERVER_PASSWORD -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential($SERVER_USER, $securePassword)

# اتصال به سرور
Write-Host "🔌 اتصال به سرور..." -ForegroundColor Yellow
try {
    $session = New-SSHSession -ComputerName $SERVER_IP -Credential $credential -AcceptKey
    Write-Host "✅ اتصال برقرار شد" -ForegroundColor Green
} catch {
    Write-Host "❌ خطا در اتصال: $_" -ForegroundColor Red
    exit 1
}

# ایجاد پوشه در سرور
Write-Host "📁 ایجاد پوشه در سرور..." -ForegroundColor Yellow
$result = Invoke-SSHCommand -SessionId $session.SessionId -Command "mkdir -p $REMOTE_PATH"
if ($result.ExitStatus -eq 0) {
    Write-Host "✅ پوشه ایجاد شد" -ForegroundColor Green
} else {
    Write-Host "⚠️  هشدار: $($result.Error)" -ForegroundColor Yellow
}

# لیست فایل‌های لازم برای کپی
$filesToCopy = @(
    "app.py",
    "auth.py", 
    "config.py",
    "wsgi.py",
    "requirements_production.txt",
    "gunicorn_config.py",
    "nginx_config.conf",
    "systemd_service.txt",
    "deploy_remote.sh"
)

$foldersToCopy = @(
    "templates",
    "static",
    "models",
    "routes",
    "services",
    "utils",
    "migrations"
)

# کپی فایل‌ها
Write-Host "`n📤 کپی فایل‌ها..." -ForegroundColor Yellow

foreach ($file in $filesToCopy) {
    $localFile = Join-Path $LOCAL_PATH $file
    if (Test-Path $localFile) {
        Write-Host "  📄 کپی $file..." -ForegroundColor Cyan
        Set-SCPFile -ComputerName $SERVER_IP -Credential $credential -LocalFile $localFile -RemotePath "$REMOTE_PATH/$file"
    }
}

# کپی پوشه‌ها
foreach ($folder in $foldersToCopy) {
    $localFolder = Join-Path $LOCAL_PATH $folder
    if (Test-Path $localFolder) {
        Write-Host "  📁 کپی $folder..." -ForegroundColor Cyan
        Get-ChildItem -Path $localFolder -Recurse -File | ForEach-Object {
            $relativePath = $_.FullName.Substring($LOCAL_PATH.Path.Length + 1)
            $remoteFile = "$REMOTE_PATH/$relativePath" -replace '\\', '/'
            $remoteDir = Split-Path $remoteFile -Parent
            Invoke-SSHCommand -SessionId $session.SessionId -Command "mkdir -p `"$remoteDir`"" | Out-Null
            Set-SCPFile -ComputerName $SERVER_IP -Credential $credential -LocalFile $_.FullName -RemotePath $remoteFile
        }
    }
}

Write-Host "`n✅ تمام فایل‌ها با موفقیت آپلود شدند!" -ForegroundColor Green

# بستن اتصال
Remove-SSHSession -SessionId $session.SessionId | Out-Null

Write-Host "`n📝 حالا می‌توانید اسکریپت deploy_remote.sh را در سرور اجرا کنید:" -ForegroundColor Yellow
Write-Host "  ssh $SERVER_USER@$SERVER_IP" -ForegroundColor Cyan
Write-Host "  cd $REMOTE_PATH" -ForegroundColor Cyan
Write-Host "  bash deploy_remote.sh" -ForegroundColor Cyan
