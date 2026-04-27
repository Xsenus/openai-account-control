param(
    [int]$Port = 5173,
    [string]$BackendUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$setupScript = Join-Path $PSScriptRoot "setup.ps1"
$viteCmd = Join-Path $root "frontend\node_modules\.bin\vite.cmd"

if (-not (Test-Path (Join-Path $root "frontend\node_modules"))) {
    & $setupScript -IncludeFrontend -SkipPlaywright
}

if (-not (Test-Path $viteCmd)) {
    throw "vite.cmd was not found. Run scripts\\setup.ps1 -IncludeFrontend first."
}

Set-Location (Join-Path $root "frontend")

$env:VITE_BACKEND_URL = $BackendUrl
& $viteCmd --host 0.0.0.0 --port $Port
