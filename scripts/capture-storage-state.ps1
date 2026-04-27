[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$AccountId,

    [string]$BackendUrl = "http://127.0.0.1:8000",

    [string]$PanelUsername = "admin",

    [string]$PanelPassword = "",

    [string]$OutputPath = ".\storage_state.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$captureScript = Join-Path $projectRoot "backend\scripts\capture_session.py"

if (-not (Test-Path $pythonExe)) {
    throw "Python environment not found at '$pythonExe'. Run scripts\\setup.ps1 first."
}

if (-not (Test-Path $captureScript)) {
    throw "Capture helper not found at '$captureScript'."
}

$arguments = @(
    $captureScript,
    "--backend-url", $BackendUrl,
    "--account-id", $AccountId,
    "--output", $OutputPath
)

if ($PanelUsername) {
    $arguments += @("--panel-username", $PanelUsername)
}

if ($PanelPassword) {
    $arguments += @("--panel-password", $PanelPassword)
}

& $pythonExe @arguments
