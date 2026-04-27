param(
    [switch]$IncludeFrontend,
    [switch]$SkipPlaywright
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "python is not available in PATH."
}

$venvPython = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    python -m venv .venv
}

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r backend\requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item .env.example .env
}

$envPath = Join-Path $root ".env"
$envText = Get-Content $envPath -Raw -Encoding UTF8
if ($envText -notmatch "(?m)^ENCRYPTION_KEY=") {
    $envText = $envText.TrimEnd() + "`r`nENCRYPTION_KEY=CHANGE_ME`r`n"
}

if ($envText -match "(?m)^ENCRYPTION_KEY=(|CHANGE_ME)\s*$") {
    $generatedKey = (& $venvPython -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())").Trim()
    $envText = [regex]::Replace($envText, "(?m)^ENCRYPTION_KEY=.*$", "ENCRYPTION_KEY=$generatedKey")
    Set-Content -Path $envPath -Value $envText -Encoding UTF8
    Write-Host "Generated ENCRYPTION_KEY in .env"
}

New-Item -ItemType Directory -Force -Path data, data\evidence | Out-Null

if (-not $SkipPlaywright) {
    & $venvPython -m playwright install chromium
}

if ($IncludeFrontend) {
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        throw "npm is not available in PATH."
    }

    Push-Location frontend
    try {
        for ($attempt = 1; $attempt -le 3; $attempt++) {
            npm install --prefer-offline --no-audit --no-fund
            if ($LASTEXITCODE -eq 0) {
                break
            }
            if ($attempt -eq 3) {
                throw "npm install failed with exit code $LASTEXITCODE."
            }
            Write-Warning "npm install failed on attempt $attempt. Retrying in 5 seconds..."
            Start-Sleep -Seconds 5
        }
    }
    finally {
        Pop-Location
    }
}

Write-Host "Setup complete."
