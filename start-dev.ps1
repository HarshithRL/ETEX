# Mate local dev — opens 3 terminals: Flask :5000, Vite :5173, AI Brain :8004
# Usage (from repo root): .\start-dev.ps1

$ErrorActionPreference = "Stop"

$RepoRoot = $PSScriptRoot
$VenvActivate = Join-Path $RepoRoot ".venv\Scripts\Activate.ps1"
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$DatabricksProfile = "adb-7181820732839861"

if (-not (Test-Path $Python)) {
    Write-Error "Python venv not found at $Python. Run: python -m venv .venv; pip install -r requirements.txt"
}

function Start-MateTerminal {
    param(
        [string]$Title,
        [string]$Body
    )

    $command = @"
`$Host.UI.RawUI.WindowTitle = '$Title'
$Body
"@

    Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", $command | Out-Null
}

$activate = ". '$VenvActivate'"

# Stage 1 — Flask API (must run from backend/)
Start-MateTerminal -Title "Mate 1/3 · Flask :5000" -Body @"
Set-Location '$RepoRoot\backend'
$activate
`$env:DATABRICKS_CONFIG_PROFILE = '$DatabricksProfile'
`$env:BRAIN_BASE_URL = 'http://127.0.0.1:8004'
Write-Host ''
Write-Host '=== Mate Flask API ===' -ForegroundColor Cyan
Write-Host 'http://127.0.0.1:5000' -ForegroundColor Green
Write-Host ''
& '$Python' app.py
"@

Start-Sleep -Milliseconds 400

# Stage 2 — React / Vite
Start-MateTerminal -Title "Mate 2/3 · Frontend :5173" -Body @"
Set-Location '$RepoRoot\frontend'
Write-Host ''
Write-Host '=== Mate Frontend (Vite) ===' -ForegroundColor Cyan
Write-Host 'http://localhost:5173' -ForegroundColor Green
Write-Host ''
npm run dev
"@

Start-Sleep -Milliseconds 400

# Stage 3 — AI Brain AgentServer (workspace chat + insights)
Start-MateTerminal -Title "Mate 3/3 · AI Brain :8004" -Body @"
Set-Location '$RepoRoot'
$activate
`$env:DATABRICKS_CONFIG_PROFILE = '$DatabricksProfile'
`$env:PYTHONPATH = '$RepoRoot'
Write-Host ''
Write-Host '=== Mate AI Brain ===' -ForegroundColor Cyan
Write-Host 'http://127.0.0.1:8004/health' -ForegroundColor Green
Write-Host ''
& '$Python' -m ai_brain.brain_server
"@

Write-Host ""
Write-Host "Started 3 terminals:" -ForegroundColor Green
Write-Host "  1. Flask API     -> http://127.0.0.1:5000"
Write-Host "  2. Frontend      -> http://localhost:5173"
Write-Host "  3. AI Brain      -> http://127.0.0.1:8004"
Write-Host ""
