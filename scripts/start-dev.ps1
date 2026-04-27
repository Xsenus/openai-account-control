param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$backendScript = Join-Path $PSScriptRoot "start-backend.ps1"
$frontendScript = Join-Path $PSScriptRoot "start-frontend.ps1"

$lanIp = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -notmatch '^127\.' -and
        $_.IPAddress -notmatch '^169\.254\.' -and
        $_.PrefixOrigin -ne 'WellKnown'
    } |
    Select-Object -First 1 -ExpandProperty IPAddress

Write-Host "Starting backend on port $BackendPort..."
$backendParent = Start-Process -FilePath "powershell.exe" `
    -ArgumentList @("-ExecutionPolicy", "Bypass", "-File", $backendScript, "-Port", $BackendPort) `
    -WorkingDirectory $root `
    -PassThru

Write-Host "Starting frontend on port $FrontendPort..."
$frontendParent = Start-Process -FilePath "powershell.exe" `
    -ArgumentList @("-ExecutionPolicy", "Bypass", "-File", $frontendScript, "-Port", $FrontendPort, "-BackendUrl", "http://127.0.0.1:$BackendPort") `
    -WorkingDirectory $root `
    -PassThru

Write-Host ""
Write-Host "Frontend URLs:"
Write-Host "  http://localhost:$FrontendPort"
Write-Host "  http://127.0.0.1:$FrontendPort"
if ($lanIp) {
    Write-Host "  http://$lanIp`:$FrontendPort"
}
Write-Host ""
Write-Host "Backend URLs:"
Write-Host "  http://localhost:$BackendPort"
Write-Host "  http://127.0.0.1:$BackendPort"
if ($lanIp) {
    Write-Host "  http://$lanIp`:$BackendPort"
}
Write-Host ""
Write-Host "Backend parent PID: $($backendParent.Id)"
Write-Host "Frontend parent PID: $($frontendParent.Id)"
