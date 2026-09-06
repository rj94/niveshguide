param(
    [switch]$UpdateFormulas,
    [switch]$LocalCsv,
    [switch]$LegacyVite,
    [int]$BackendPort = 8010,
    [int]$WebPort = 3000,
    [int]$FrontendPort = 5173,
    [string]$HostName = "127.0.0.1"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $ProjectRoot "backend"
$WebDir = Join-Path $ProjectRoot "web"
$FrontendDir = Join-Path $ProjectRoot "frontend"

function Test-Command {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )

    try {
        $Output = & $FilePath @Arguments 2>&1
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

function Resolve-PythonExe {
    $Candidates = @(
        (Join-Path $BackendDir ".venv\Scripts\python.exe"),
        "python",
        "py",
        "C:\Users\rahul\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    )

    foreach ($Candidate in $Candidates) {
        if ($Candidate -like "*\*" -and -not (Test-Path $Candidate)) {
            continue
        }
        if (Test-Command $Candidate @("-c", "import fastapi, sqlalchemy, uvicorn")) {
            return $Candidate
        }
    }

    throw "No working Python executable with backend dependencies found. Recreate backend\.venv and run pip install -r backend\requirements.txt, or add a prepared Python to PATH."
}

function Resolve-NodeExe {
    $Candidates = @(
        "node",
        "C:\Users\rahul\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
    )

    foreach ($Candidate in $Candidates) {
        if ($Candidate -like "*\*" -and -not (Test-Path $Candidate)) {
            continue
        }
        if (Test-Command $Candidate @("--version")) {
            return $Candidate
        }
    }

    throw "No working Node.js executable found. Install Node.js or add node to PATH."
}

function Resolve-NpmExe {
    $Candidates = @(
        "npm",
        "C:\Users\rahul\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\npm.cmd"
    )
    foreach ($Candidate in $Candidates) {
        if ($Candidate -like "*\*" -and -not (Test-Path $Candidate)) {
            continue
        }
        if (Test-Command $Candidate @("--version")) {
            return $Candidate
        }
    }
    throw "No working npm executable found."
}

function Invoke-Step {
    param(
        [string]$Title,
        [scriptblock]$Command
    )

    Write-Host ""
    Write-Host "==> $Title" -ForegroundColor Cyan
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Title failed with exit code $LASTEXITCODE"
    }
}

function Stop-StartedProcess {
    param([System.Diagnostics.Process]$Process)

    if ($null -ne $Process -and -not $Process.HasExited) {
        Stop-Process -Id $Process.Id -Force
    }
}

$PythonExe = Resolve-PythonExe
$NodeExe = Resolve-NodeExe
$NpmExe = Resolve-NpmExe

if (-not (Test-Path $WebDir)) {
    throw "Primary UI folder missing: $WebDir (MarketPlatform Next.js app)."
}

Push-Location $BackendDir
try {
    $RefreshArgs = @("-m", "cli", "refresh")
    if (-not $UpdateFormulas) {
        $RefreshArgs += "--skip-formulas"
    }
    if ($LocalCsv) {
        $RefreshArgs += "--local-csv"
    }

    Invoke-Step "Sync spreadsheet data into the database and calculate latest indicators" {
        & $PythonExe @RefreshArgs
    }
}
finally {
    Pop-Location
}

if (-not (Test-Path (Join-Path $WebDir "node_modules"))) {
    Invoke-Step "Install Next.js dependencies in web/" {
        Push-Location $WebDir
        try {
            & $NpmExe install
        }
        finally {
            Pop-Location
        }
    }
}

Write-Host ""
Write-Host "==> Starting API on http://${HostName}:$BackendPort" -ForegroundColor Cyan
$BackendProcess = Start-Process `
    -FilePath $PythonExe `
    -ArgumentList @("-m", "cli", "serve", "--host", $HostName, "--port", "$BackendPort") `
    -WorkingDirectory $BackendDir `
    -NoNewWindow `
    -PassThru

Write-Host "==> Starting MarketPlatform UI on http://${HostName}:$WebPort" -ForegroundColor Cyan
$env:NEXT_PUBLIC_API_URL = "http://${HostName}:$BackendPort/api/v1"
$WebProcess = Start-Process `
    -FilePath $NpmExe `
    -ArgumentList @("run", "dev", "--", "-H", $HostName, "-p", "$WebPort") `
    -WorkingDirectory $WebDir `
    -NoNewWindow `
    -PassThru

$FrontendProcess = $null
if ($LegacyVite) {
    $ViteScript = Join-Path $FrontendDir "node_modules\vite\bin\vite.js"
    if (-not (Test-Path $ViteScript)) {
        throw "Vite was not found in frontend\node_modules. Run npm install in the frontend folder."
    }
    Write-Host "==> Starting legacy Vite desk on http://${HostName}:$FrontendPort" -ForegroundColor Cyan
    $FrontendProcess = Start-Process `
        -FilePath $NodeExe `
        -ArgumentList @($ViteScript, "--host", $HostName, "--port", "$FrontendPort") `
        -WorkingDirectory $FrontendDir `
        -NoNewWindow `
        -PassThru
}

try {
    Write-Host ""
    Write-Host "Trade app is running with the latest database data." -ForegroundColor Green
    Write-Host "Open UI:  http://${HostName}:$WebPort"
    Write-Host "API:      http://${HostName}:$BackendPort"
    Write-Host "API v1:   http://${HostName}:$BackendPort/api/v1"
    if ($LegacyVite) {
        Write-Host "Legacy:   http://${HostName}:$FrontendPort"
    }
    Write-Host "Press Ctrl+C to stop servers."

    while (-not $BackendProcess.HasExited -and -not $WebProcess.HasExited) {
        if ($null -ne $FrontendProcess -and $FrontendProcess.HasExited) {
            throw "Legacy Vite stopped unexpectedly with exit code $($FrontendProcess.ExitCode)"
        }
        Start-Sleep -Seconds 2
    }

    if ($BackendProcess.HasExited) {
        throw "Backend stopped unexpectedly with exit code $($BackendProcess.ExitCode)"
    }
    if ($WebProcess.HasExited) {
        throw "Next.js UI stopped unexpectedly with exit code $($WebProcess.ExitCode)"
    }
}
finally {
    Stop-StartedProcess $BackendProcess
    Stop-StartedProcess $WebProcess
    Stop-StartedProcess $FrontendProcess
}
