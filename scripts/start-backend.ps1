param(
    [int]$Port = 8000,
    [switch]$Reload
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$setupScript = Join-Path $PSScriptRoot "setup.ps1"
$venvPython = Join-Path $root ".venv\Scripts\python.exe"
$envPath = Join-Path $root ".env"

if (-not (Test-Path $venvPython)) {
    & $setupScript -SkipPlaywright
}
elseif (-not (Test-Path $envPath)) {
    & $setupScript -SkipPlaywright
}
else {
    $envText = Get-Content $envPath -Raw -Encoding UTF8
    if ($envText -match "(?m)^ENCRYPTION_KEY=(|CHANGE_ME)\s*$") {
        & $setupScript -SkipPlaywright
    }
}

Set-Location $root
New-Item -ItemType Directory -Force -Path data, data\evidence | Out-Null

$arguments = @(
    "-m",
    "uvicorn",
    "backend.app.main:app",
    "--host",
    "0.0.0.0",
    "--port",
    $Port.ToString()
)

if ($Reload) {
    $arguments += "--reload"
}

& $venvPython @arguments
