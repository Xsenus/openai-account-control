param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$Username = "",
    [string]$Password = ""
)

$ErrorActionPreference = "Stop"

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$health = Invoke-RestMethod "$BaseUrl/api/health" -WebSession $session

if ($Username -and $Password) {
    $loginPayload = @{
        username = $Username
        password = $Password
    } | ConvertTo-Json

    Invoke-RestMethod `
        -Method Post `
        -Uri "$BaseUrl/api/auth/login" `
        -ContentType "application/json" `
        -Body $loginPayload `
        -WebSession $session | Out-Null
}

$dashboard = Invoke-RestMethod "$BaseUrl/api/dashboard/summary" -WebSession $session
$root = Invoke-WebRequest -UseBasicParsing "$BaseUrl/" -WebSession $session

[PSCustomObject]@{
    HealthStatus   = $health.status
    App            = $health.app
    RootStatusCode = $root.StatusCode
    TotalAccounts  = $dashboard.counters.total_accounts
    LastScanAt     = $dashboard.counters.last_scan_at
} | Format-List
