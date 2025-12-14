# اسکریپت PowerShell برای اتصال به سرور
$ErrorActionPreference = "Stop"

$SERVER_IP = $env:CAFE_SERVER_IP
$SERVER_USER = $env:CAFE_SERVER_USER
$SERVER_PASSWORD = $env:CAFE_SERVER_PASSWORD

if (-not $SERVER_IP) { throw "CAFE_SERVER_IP را در Environment Variables تنظیم کنید." }
if (-not $SERVER_USER) { throw "CAFE_SERVER_USER را در Environment Variables تنظیم کنید." }
if (-not $SERVER_PASSWORD) { throw "CAFE_SERVER_PASSWORD را در Environment Variables تنظیم کنید." }

Write-Host "🔌 اتصال به سرور $SERVER_IP با کاربر $SERVER_USER..." -ForegroundColor Green

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
Write-Host "🔌 در حال اتصال..." -ForegroundColor Yellow
try {
    $session = New-SSHSession -ComputerName $SERVER_IP -Credential $credential -AcceptKey
    Write-Host "✅ اتصال برقرار شد! Session ID: $($session.SessionId)" -ForegroundColor Green
    Write-Host ""
    Write-Host "📝 برای اجرای دستورات از Invoke-SSHCommand استفاده کنید:" -ForegroundColor Cyan
    Write-Host "   Invoke-SSHCommand -SessionId $($session.SessionId) -Command 'ls -la'" -ForegroundColor White
    Write-Host ""
    Write-Host "📝 برای اتصال تعاملی SSH، از دستور زیر استفاده کنید:" -ForegroundColor Cyan
    Write-Host "   ssh $SERVER_USER@$SERVER_IP" -ForegroundColor White
    Write-Host ""
    Write-Host "💡 رمز عبور از ENV خوانده شد." -ForegroundColor Yellow
    
    # ذخیره session ID برای استفاده بعدی
    $session | Export-Clixml -Path ".\ssh_session.xml"
    Write-Host "💾 Session در فایل ssh_session.xml ذخیره شد" -ForegroundColor Green
    
} catch {
    Write-Host "❌ خطا در اتصال: $_" -ForegroundColor Red
    exit 1
}




