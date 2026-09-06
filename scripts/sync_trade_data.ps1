param(
    [switch]$LocalCsv
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $ProjectRoot "backend"

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
        "py"
    )

    foreach ($Candidate in $Candidates) {
        if ($Candidate -like "*\*" -and -not (Test-Path $Candidate)) {
            continue
        }
        if (Test-Command $Candidate @("-c", "import fastapi, sqlalchemy, uvicorn")) {
            return $Candidate
        }
    }

    throw "No working Python executable with backend dependencies found. Recreate backend\.venv and run pip install -r backend\requirements.txt."
}

$PythonExe = Resolve-PythonExe
$RefreshArgs = @("-m", "cli", "refresh", "--skip-formulas")
if ($LocalCsv) {
    $RefreshArgs += "--local-csv"
}

Push-Location $BackendDir
try {
    & $PythonExe @RefreshArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Trade data sync failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
