# Setup and Run Script for Cafe App
Write-Host "=== Cafe App Setup ===" -ForegroundColor Cyan
Write-Host ""

# Change to script directory
Set-Location $PSScriptRoot

# Check Python
Write-Host "Checking Python installation..." -ForegroundColor Yellow
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "ERROR: Python not found in PATH!" -ForegroundColor Red
    Write-Host "Please install Python or add it to your PATH." -ForegroundColor Red
    pause
    exit 1
}

$pythonPath = $pythonCmd.Source
Write-Host "Python found at: $pythonPath" -ForegroundColor Green

# Check Flask
Write-Host ""
Write-Host "Checking Flask installation..." -ForegroundColor Yellow
$flaskCheck = & python -c "import flask; print('OK')" 2>&1
if ($LASTEXITCODE -ne 0 -or $flaskCheck -notmatch "OK") {
    Write-Host "Flask not found! Installing Flask and dependencies..." -ForegroundColor Yellow
    & python -m pip install Flask==3.0.2 Flask-Login Flask-SQLAlchemy Flask-Migrate SQLAlchemy
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to install Flask!" -ForegroundColor Red
        pause
        exit 1
    }
    Write-Host "Flask installed successfully!" -ForegroundColor Green
} else {
    Write-Host "Flask is already installed." -ForegroundColor Green
}

# Verify installation
Write-Host ""
Write-Host "Verifying installation..." -ForegroundColor Yellow
& python -c "from flask import Flask; print('Flask version:', Flask.__version__ if hasattr(Flask, '__version__') else '3.0.2')" 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Verification successful!" -ForegroundColor Green
} else {
    Write-Host "ERROR: Flask verification failed!" -ForegroundColor Red
    pause
    exit 1
}

# Run the app
Write-Host ""
Write-Host "Starting Flask application..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

& python app.py
