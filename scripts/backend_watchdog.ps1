# OMEGA-ARC backend watchdog (2026-11-06).
#
# Run by the "OMEGA-ARC Backend Watchdog" scheduled task at logon and every 5 minutes.
# Keeps the backend (and the Ollama it depends on) up so the phones can always reach it
# through Tailscale (https://artoo.sungrazer-interval.ts.net).
#
# Health is checked by HTTP, NOT by Get-NetTCPConnection: on this host Windows sometimes
# reports the backend's 0.0.0.0:8001 socket without a "Listen" state while it is serving
# fine, so a port-table guard can wrongly decide it is down and start a duplicate.
# Doing nothing is the common case and costs one local HTTP request.

$ErrorActionPreference = 'Stop'

$projectRoot     = Split-Path -Parent $PSScriptRoot
$backendRoot     = Join-Path $projectRoot 'backend'
$logRoot         = Join-Path $projectRoot '.runtime-logs'
$pythonExe       = Join-Path $backendRoot '.venv\Scripts\python.exe'
$backendLauncher = Join-Path $PSScriptRoot 'launch_backend.py'
$ollamaExe       = 'C:\Users\BillH\AppData\Local\Programs\Ollama\ollama.exe'
$watchLog        = Join-Path $logRoot 'watchdog.log'

New-Item -ItemType Directory -Path $logRoot -Force | Out-Null

function Write-Watch([string]$Message) {
    $line = '{0:yyyy-MM-dd HH:mm:ss}  {1}' -f (Get-Date), $Message
    Add-Content -Path $watchLog -Value $line
    # Keep the log small: last 500 lines.
    $lines = Get-Content $watchLog
    if ($lines.Count -gt 600) { $lines | Select-Object -Last 500 | Set-Content $watchLog }
}

function Test-Http([string]$Uri) {
    try {
        $r = Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec 5
        return ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500)
    } catch {
        # A 4xx/5xx still means something is answering on the port.
        if ($_.Exception.Response) { return $true }
        return $false
    }
}

function Test-BackendProcess {
    # A backend that is still starting up answers nothing yet; do not start a second one.
    $procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like '*launch_backend.py*' }
    return [bool]$procs
}

function Rotate-Log([string]$Name) {
    $path = Join-Path $logRoot $Name
    if (Test-Path $path) { Copy-Item $path "$path.prev" -Force }
    return $path
}

# --- Ollama (chat models) -------------------------------------------------------------
if (-not (Test-Http 'http://127.0.0.1:11434/api/tags')) {
    $running = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $ollamaExe }
    if ($running) {
        Write-Watch "ollama: not answering but process alive (pid $($running.Id -join ',')); leaving it alone"
    } else {
        Start-Process -FilePath $ollamaExe -ArgumentList @('serve') -WindowStyle Hidden `
            -RedirectStandardOutput (Rotate-Log 'ollama.stdout.log') `
            -RedirectStandardError  (Rotate-Log 'ollama.stderr.log') | Out-Null
        Write-Watch 'ollama: was down, started'
    }
}

# --- Backend ------------------------------------------------------------------------
if (Test-Http 'http://127.0.0.1:8001/') { exit 0 }

if (Test-BackendProcess) {
    Write-Watch 'backend: not answering yet, but a launch_backend.py process exists (starting up?); waiting'
    exit 0
}

Start-Process -FilePath $pythonExe -WorkingDirectory $backendRoot -WindowStyle Hidden `
    -ArgumentList @('-u', "`"$backendLauncher`"") `
    -RedirectStandardOutput (Rotate-Log 'backend.stdout.log') `
    -RedirectStandardError  (Rotate-Log 'backend.stderr.log') | Out-Null
Write-Watch 'backend: was down, started'
