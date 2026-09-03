# Mate local dev — stop Flask :5000, Vite :5173, AI Brain :8004
# Usage (from repo root): .\stop-dev.ps1

$ErrorActionPreference = "Continue"

$DevPorts = @(
    @{ Port = 5000; Label = "Flask API" },
    @{ Port = 5173; Label = "Vite frontend" },
    @{ Port = 8004; Label = "AI Brain" },
    @{ Port = 8000; Label = "Agent FastAPI (legacy)" }
)

function Get-PortListenerPids {
    param([int]$Port)

    $pids = [System.Collections.Generic.HashSet[int]]::new()

    try {
        $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
        foreach ($conn in $connections) {
            if ($conn.OwningProcess -gt 0) {
                [void]$pids.Add([int]$conn.OwningProcess)
            }
        }
    }
    catch {
        $pattern = ":$Port\s"
        $lines = netstat -ano | Select-String "LISTENING" | Select-String $pattern
        foreach ($line in $lines) {
            $parts = ($line -split "\s+") | Where-Object { $_ -ne "" }
            if ($parts.Count -ge 1) {
                $procId = [int]$parts[-1]
                if ($procId -gt 0) {
                    [void]$pids.Add($procId)
                }
            }
        }
    }

    return @($pids)
}

function Get-ProcessSummary {
    param([int]$ProcId)

    try {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcId" -ErrorAction Stop
        $cmd = $proc.CommandLine
        if (-not $cmd) {
            $cmd = $proc.Name
        }
        if ($cmd.Length -gt 120) {
            $cmd = $cmd.Substring(0, 117) + "..."
        }
        return $cmd
    }
    catch {
        return "(process $ProcId)"
    }
}

function Stop-Listener {
    param(
        [int]$ProcId,
        [string]$Label
    )

    $summary = Get-ProcessSummary -ProcId $ProcId
    Write-Host "  Stopping PID $ProcId ($Label): $summary" -ForegroundColor Yellow
    $null = taskkill /F /PID $ProcId /T 2>&1
}

Write-Host ""
Write-Host "=== Mate stop-dev ===" -ForegroundColor Cyan
Write-Host "Targets: :5000 Flask, :5173 Vite, :8004 AI Brain" -ForegroundColor DarkGray
Write-Host ""

$targets = @{}
foreach ($entry in $DevPorts) {
    foreach ($procId in (Get-PortListenerPids -Port $entry.Port)) {
        if (-not $targets.ContainsKey($procId)) {
            $targets[$procId] = $entry.Label
        }
    }
}

if ($targets.Count -eq 0) {
    Write-Host "No listeners on ports 5000, 5173, 8004, or 8000." -ForegroundColor Green
    Write-Host ""
    exit 0
}

Write-Host "Found $($targets.Count) listener process(es):" -ForegroundColor White
foreach ($kv in $targets.GetEnumerator() | Sort-Object Name) {
    Stop-Listener -ProcId $kv.Key -Label $kv.Value
}

Start-Sleep -Seconds 2

Write-Host ""
Write-Host "Port check:" -ForegroundColor Cyan
$stillListening = $false
foreach ($entry in $DevPorts) {
    $remaining = Get-PortListenerPids -Port $entry.Port
    if ($remaining.Count -gt 0) {
        $stillListening = $true
        Write-Host "  :$($entry.Port) still listening (PID $($remaining -join ', '))" -ForegroundColor Red
    }
    else {
        Write-Host "  :$($entry.Port) free ($($entry.Label))" -ForegroundColor Green
    }
}

if ($stillListening) {
    Write-Host ""
    Write-Host "Some ports are still in use. Close the Mate terminal windows or run stop-dev again." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "All Mate dev ports stopped." -ForegroundColor Green
Write-Host "Restart with: .\start-dev.ps1" -ForegroundColor DarkGray
Write-Host ""
