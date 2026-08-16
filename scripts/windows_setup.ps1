param(
    [string]$ProjectPath,
    [switch]$CheckOnly,
    [switch]$NoPersist
)

# Windows PowerShell 5 maps native stderr to PowerShell errors. We inspect each
# native exit code explicitly, so warnings must not abort the installer.
$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$Host.UI.RawUI.WindowTitle = 'Cafe Platform - Setup and Run'

function Write-Step([string]$Message) { Write-Host "`n[*] $Message" -ForegroundColor Cyan }
function Write-Ok([string]$Message) { Write-Host "[OK] $Message" -ForegroundColor Green }
function Write-Warn([string]$Message) { Write-Host "[!] $Message" -ForegroundColor Yellow }
function Stop-WithMessage([string]$Message) {
    Write-Host "`n[ERROR] $Message" -ForegroundColor Red
    throw $Message
}

function Test-CafeProject([string]$Path) {
    if (-not $Path -or -not (Test-Path -LiteralPath $Path -PathType Container)) { return $false }
    return (
        (Test-Path -LiteralPath (Join-Path $Path 'app.py') -PathType Leaf) -and
        (Test-Path -LiteralPath (Join-Path $Path 'wsgi.py') -PathType Leaf) -and
        (Test-Path -LiteralPath (Join-Path $Path 'requirements_minimal.txt') -PathType Leaf)
    )
}

function Resolve-Python {
    $commands = @()
    if (Get-Command py.exe -ErrorAction SilentlyContinue) {
        foreach ($version in @('-3.13', '-3.12', '-3.11')) {
            $commands += ,@('py.exe', $version)
        }
        $commands += ,@('py.exe')
    }
    if (Get-Command python.exe -ErrorAction SilentlyContinue) { $commands += ,@('python.exe') }

    $knownPaths = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe')
    )
    foreach ($known in $knownPaths) {
        if (Test-Path -LiteralPath $known) { $commands += ,@($known) }
    }

    foreach ($command in $commands) {
        $exe = $command[0]
        $prefix = @($command | Select-Object -Skip 1)
        try {
            $result = & $exe @prefix -c "import sys; print(sys.executable); print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
            if ($LASTEXITCODE -eq 0 -and $result.Count -ge 2) {
                $parts = $result[-1].Split('.')
                if ([int]$parts[0] -eq 3 -and [int]$parts[1] -ge 11) {
                    return [PSCustomObject]@{ Exe = $exe; Prefix = $prefix; Path = $result[-2]; Version = $result[-1] }
                }
            }
        } catch { }
    }
    return $null
}

function Test-CafeHttp([int]$Port) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/login" -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    } catch { return $false }
}

try {
    Write-Host '============================================================' -ForegroundColor DarkCyan
    Write-Host '             Cafe Platform One-Click Installer' -ForegroundColor Cyan
    Write-Host '============================================================' -ForegroundColor DarkCyan

    $stateRoot = Join-Path $env:LOCALAPPDATA 'CafePlatform'
    $pathState = Join-Path $stateRoot 'project-path.txt'
    $scriptProject = Split-Path -Parent $PSScriptRoot

    if (-not $ProjectPath -and (Test-Path -LiteralPath $pathState)) {
        $savedPath = (Get-Content -LiteralPath $pathState -Raw -ErrorAction SilentlyContinue).Trim()
        if (Test-CafeProject $savedPath) {
            $ProjectPath = $savedPath
            Write-Ok "Saved project path loaded: $ProjectPath"
        }
    }

    if (-not $ProjectPath) {
        Write-Step 'Select project folder (first run only)'
        Write-Host "Suggested folder: $scriptProject"
        $enteredPath = Read-Host 'Paste the folder containing app.py, or press Enter to use the suggested folder'
        $ProjectPath = if ([string]::IsNullOrWhiteSpace($enteredPath)) { $scriptProject } else { $enteredPath.Trim().Trim('"') }
    }

    if (-not (Test-CafeProject $ProjectPath)) {
        Stop-WithMessage 'Invalid folder. It must contain app.py, wsgi.py and requirements_minimal.txt.'
    }
    $ProjectPath = (Resolve-Path -LiteralPath $ProjectPath).Path
    if (-not $NoPersist) {
        New-Item -ItemType Directory -Path $stateRoot -Force | Out-Null
        Set-Content -LiteralPath $pathState -Value $ProjectPath -Encoding UTF8
        Write-Ok "Project path saved for future runs: $pathState"
    }
    Set-Location -LiteralPath $ProjectPath

    Write-Step 'Checking Python 3.11 or newer'
    $python = Resolve-Python
    if (-not $python) {
        Write-Warn 'A supported Python installation was not found.'
        $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
        if (-not $winget) {
            Stop-WithMessage 'Python and winget are unavailable. Install Python 3.12 from https://www.python.org/downloads/ and enable Add Python to PATH.'
        }
        Write-Host 'Installing Python 3.12 with Windows Package Manager. This may take a few minutes.'
        & winget.exe install --id Python.Python.3.12 --exact --source winget --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -ne 0) { Stop-WithMessage 'Automatic Python installation failed.' }
        $python = Resolve-Python
        if (-not $python) { Stop-WithMessage 'Python was installed but is not visible yet. Close this window and run INSTALL_AND_RUN.bat again.' }
    }
    Write-Ok "Python $($python.Version): $($python.Path)"

    $venvRoot = Join-Path $ProjectPath '.venv'
    $venvPython = Join-Path $venvRoot 'Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $venvPython)) {
        Write-Step 'Creating the project virtual environment'
        & $python.Exe @($python.Prefix) -m venv $venvRoot
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $venvPython)) { Stop-WithMessage 'Could not create the virtual environment.' }
        Write-Ok 'Virtual environment created.'
    } else {
        Write-Ok 'Project virtual environment is already available.'
    }

    Write-Step 'Checking backend, database and web dependencies'
    $requirementFile = Join-Path $ProjectPath 'requirements_minimal.txt'
    $requirementHash = (Get-FileHash -LiteralPath $requirementFile -Algorithm SHA256).Hash
    $setupRoot = Join-Path $ProjectPath '.setup'
    $hashFile = Join-Path $setupRoot 'requirements.sha256'
    $oldHash = if (Test-Path -LiteralPath $hashFile) { (Get-Content -LiteralPath $hashFile -Raw).Trim() } else { '' }
    & $venvPython -c "import flask, flask_login, flask_sqlalchemy, flask_migrate, sqlalchemy, jdatetime, pytz, requests, waitress" 2>$null
    $importsReady = $LASTEXITCODE -eq 0

    if (-not $importsReady -or $oldHash -ne $requirementHash) {
        Write-Host 'Dependencies are missing or changed. Installation is starting.'
        & $venvPython -m pip install --upgrade pip setuptools wheel
        if ($LASTEXITCODE -ne 0) { Stop-WithMessage 'Could not update Python installation tools. Check the internet connection.' }
        & $venvPython -m pip install --requirement $requirementFile
        if ($LASTEXITCODE -ne 0) { Stop-WithMessage 'Dependency installation failed. Review the error above.' }
        New-Item -ItemType Directory -Path $setupRoot -Force | Out-Null
        Set-Content -LiteralPath $hashFile -Value $requirementHash -Encoding ASCII
        Write-Ok 'All required dependencies are installed.'
    } else {
        Write-Ok 'All dependencies match the current project version.'
    }

    Write-Step 'Checking application and database structure'
    $env:PYTHONUTF8 = '1'
    $env:PYTHONIOENCODING = 'utf-8'
    & $venvPython -c "from app import create_app; app=create_app(); print('APP_OK', len(app.url_map._rules))"
    if ($LASTEXITCODE -ne 0) { Stop-WithMessage 'Application validation failed.' }
    Write-Ok 'Application, master database and local migrations are ready.'

    if ($CheckOnly) {
        Write-Ok 'Validation completed successfully. The server was not started.'
        exit 0
    }

    $port = 5000
    if (Test-CafeHttp $port) {
        Write-Ok "Cafe Platform is already running at http://127.0.0.1:$port."
        Start-Process "http://127.0.0.1:$port"
        Read-Host 'Press Enter to close this window. The existing server will keep running'
        exit 0
    }
    $tcp = [System.Net.Sockets.TcpClient]::new()
    try {
        $connectTask = $tcp.ConnectAsync('127.0.0.1', $port)
        if ($connectTask.Wait(1500) -and $tcp.Connected) {
            Stop-WithMessage "Port $port is used by another application. Close it and try again."
        }
    } catch { } finally {
        $tcp.Dispose()
    }

    Write-Step 'Starting Cafe Platform'
    Write-Host "URL: http://127.0.0.1:$port" -ForegroundColor Green
    Write-Host 'The default browser opens automatically after the server is ready.'
    Write-Host 'Press Ctrl+C to stop the server. This window stays open.' -ForegroundColor Yellow

    $browserJob = Start-Job -ScriptBlock {
        param($Url)
        for ($attempt = 0; $attempt -lt 90; $attempt++) {
            try {
                $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
                if ($response.StatusCode -ge 200) { Start-Process $Url; return }
            } catch { }
            Start-Sleep -Seconds 1
        }
    } -ArgumentList "http://127.0.0.1:$port"

    try {
        & $venvPython -m waitress --listen="127.0.0.1:$port" --threads=8 wsgi:app
        $serverExit = $LASTEXITCODE
    } finally {
        if ($browserJob) { Stop-Job $browserJob -ErrorAction SilentlyContinue; Remove-Job $browserJob -Force -ErrorAction SilentlyContinue }
    }
    if ($serverExit -ne 0) { Stop-WithMessage "The server stopped with exit code $serverExit." }
    exit 0
} catch {
    Write-Host "`nERROR DETAIL: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "`nCheck the internet connection, project path and the error above." -ForegroundColor Yellow
    Write-Host 'This window stays open so the error can be read.' -ForegroundColor Yellow
    Read-Host 'Press Enter to finish'
    exit 1
}
