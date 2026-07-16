param(
    [int]$BackendPort = 8001,
    [int]$FrontendPort = 5173
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$BackendPath = Join-Path $RepoRoot "backend"
$FrontendPath = Join-Path $RepoRoot "frontend"
$PythonPath = Join-Path $BackendPath ".venv\Scripts\python.exe"

Write-Host ""
Write-Host "OMEGA-ARC Launch Sequence"
Write-Host "Repository: $RepoRoot"
Write-Host "Backend:    http://127.0.0.1:$BackendPort"
Write-Host "Frontend:   http://localhost:$FrontendPort"
Write-Host ""

if (-not (Test-Path $PythonPath)) {
    throw "Backend Python environment not found: $PythonPath"
}

if (-not (Test-Path (Join-Path $BackendPath "app.py"))) {
    throw "Backend app.py was not found."
}

if (-not (Test-Path (Join-Path $FrontendPath "package.json"))) {
    throw "Frontend package.json was not found."
}

$BackendCommand = @"
Set-Location '$BackendPath'
`$env:PYTHONPATH = '$BackendPath'
& '$PythonPath' -m uvicorn app:app --reload --host 127.0.0.1 --port $BackendPort
"@

$FrontendCommand = @"
Set-Location '$FrontendPath'
`$env:VITE_API_URL = 'http://127.0.0.1:$BackendPort'
npm run dev -- --host 127.0.0.1 --port $FrontendPort
"@

Start-Process powershell.exe -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command", $BackendCommand
)

Start-Sleep -Seconds 2

Start-Process powershell.exe -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command", $FrontendCommand
)

Start-Sleep -Seconds 4

Start-Process "http://localhost:$FrontendPort"

Write-Host "OMEGA-ARC launch sequence initiated."
